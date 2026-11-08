"""Tests for the invoice CSV export route."""

from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import StringIO

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.orders import OrderStatus
from app.infra.clock import OffsetClock
from app.modules.invoices.models import Invoice, InvoiceStatus
from app.modules.orders.models import Order
from app.modules.orders.seed import seed_products
from tests.invoices.helpers import assert_problem

EXPORT_HEADER = [
    "id",
    "number",
    "status",
    "order_id",
    "order_number",
    "customer_name",
    "tax_id",
    "subtotal",
    "tax_rate",
    "tax",
    "total",
    "created_at",
    "updated_at",
]
BASE = datetime(2026, 1, 1, 14, 0, tzinfo=UTC)
TAX_RATE = Decimal("10.00")
STATUSES = (InvoiceStatus.ISSUED, InvoiceStatus.PAID, InvoiceStatus.VOID)


def csv_rows(text: str) -> list[list[str]]:
    return list(csv.reader(StringIO(text)))


def many_orders() -> list[Order]:
    return [
        Order(
            id=identifier,
            number=f"PED-{identifier:04d}",
            status=OrderStatus.CONFIRMED,
            customer_id=(identifier - 1) % 10 + 1,
            lines=(),
            tax_rate=TAX_RATE,
            version=1,
            created_at=BASE + timedelta(minutes=identifier),
            updated_at=BASE + timedelta(minutes=identifier),
            invoice_id=None,
        )
        for identifier in range(1, 46)
    ]


def many_invoices() -> list[Invoice]:
    invoices: list[Invoice] = []
    for identifier in range(1, 46):
        created_at = BASE + timedelta(minutes=identifier)
        invoices.append(
            Invoice(
                id=identifier,
                number=f"FAC-{identifier:04d}",
                status=STATUSES[(identifier - 1) % len(STATUSES)],
                order_id=identifier,
                order_number=f"PED-{identifier:04d}",
                customer_id=(identifier - 1) % 10 + 1,
                customer_name=f"Customer {identifier:02d}",
                customer_tax_id=f"TAX-{identifier:03d}",
                customer_address=None,
                lines=(),
                subtotal=Decimal("10.00"),
                tax_rate=TAX_RATE,
                tax=Decimal("1.00"),
                total=Decimal("11.00"),
                version=1,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    return invoices


def replace_invoices(app: FastAPI) -> None:
    app.state.order_store.replace_all(seed_products(), many_orders(), TAX_RATE)
    app.state.invoice_store.replace_all(many_invoices(), [])


def exported_rows(response, header: list[str]) -> list[dict[str, str]]:
    rows = csv_rows(response.text)
    assert rows[0] == header
    return [dict(zip(header, row, strict=True)) for row in rows[1:]]


def test_the_export_has_the_header_and_every_row_of_the_list(
    app: FastAPI,
    clients: dict[str, TestClient],
) -> None:
    replace_invoices(app)

    listed = clients["finance"].get("/api/invoices")
    response = clients["finance"].get("/api/invoices/export")

    assert listed.status_code == 200
    assert response.status_code == 200
    rows = csv_rows(response.text)
    assert rows[0] == EXPORT_HEADER
    assert len(rows) - 1 == listed.json()["total"] == 45
    assert response.text.endswith("\r\n")


def test_the_export_follows_the_sort_of_the_list(
    app: FastAPI,
    clients: dict[str, TestClient],
) -> None:
    replace_invoices(app)

    ascending = clients["finance"].get(
        "/api/invoices/export",
        params={"sort": "number", "direction": "asc"},
    )
    descending = clients["finance"].get(
        "/api/invoices/export",
        params={"sort": "number", "direction": "desc"},
    )

    assert [row["id"] for row in exported_rows(ascending, EXPORT_HEADER)] == [
        str(identifier) for identifier in range(1, 46)
    ]
    assert [row["id"] for row in exported_rows(descending, EXPORT_HEADER)] == [
        str(identifier) for identifier in range(45, 0, -1)
    ]


@pytest.mark.parametrize(
    "params",
    [
        {"q": "FAC-0007"},
        {"status": "issued"},
        {"order_id": 3},
        {"status": "issued", "order_id": 1},
    ],
)
def test_the_export_reuses_the_list_filters(
    app: FastAPI,
    clients: dict[str, TestClient],
    params: dict[str, object],
) -> None:
    replace_invoices(app)

    listed = clients["finance"].get("/api/invoices", params=params)
    response = clients["finance"].get("/api/invoices/export", params=params)

    assert listed.status_code == 200
    assert response.status_code == 200
    assert len(csv_rows(response.text)) - 1 == listed.json()["total"]


@pytest.mark.parametrize("page", [0, 2, 1_000_001])
def test_the_export_ignores_page(
    app: FastAPI,
    clients: dict[str, TestClient],
    page: int,
) -> None:
    replace_invoices(app)

    response = clients["finance"].get("/api/invoices/export", params={"page": page})

    assert response.status_code == 200
    assert len(csv_rows(response.text)) - 1 == 45


def test_the_export_headers_come_from_the_application_clock(
    clients: dict[str, TestClient],
    app_clock: OffsetClock,
) -> None:
    moved = app_clock.now() + timedelta(hours=2)
    app_clock.advance(timedelta(hours=2))
    try:
        response = clients["finance"].get("/api/invoices/export")
    finally:
        app_clock.set_offset(timedelta(0))

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"] == (
        f'attachment; filename="invoices-{moved:%Y%m%d}.csv"'
    )
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]


def test_the_export_requires_a_session(app: FastAPI) -> None:
    response = TestClient(app).get("/api/invoices/export")

    assert_problem(response, 401, "UNAUTHENTICATED")


@pytest.mark.parametrize(
    "params",
    [{"status": "deleted"}, {"sort": "unknown"}, {"direction": "up"}],
)
def test_an_invalid_query_has_the_same_body_as_the_list(
    clients: dict[str, TestClient],
    params: dict[str, str],
) -> None:
    listed = clients["finance"].get("/api/invoices", params=params)
    exported = clients["finance"].get("/api/invoices/export", params=params)

    assert exported.status_code == listed.status_code == 422
    assert exported.json() == listed.json()


def test_the_invoice_row_carries_the_snapshot_name_and_tax_id(
    app: FastAPI,
    clients: dict[str, TestClient],
) -> None:
    replace_invoices(app)

    response = clients["finance"].get("/api/invoices/export")
    rows = {row["number"]: row for row in exported_rows(response, EXPORT_HEADER)}

    assert rows["FAC-0003"]["customer_name"] == "Customer 03"
    assert rows["FAC-0003"]["tax_id"] == "TAX-003"
    assert rows["FAC-0003"]["order_number"] == "PED-0003"
    assert rows["FAC-0003"]["total"] == "11.00"


@pytest.mark.parametrize("role", ["admin", "sales", "finance", "readonly"])
def test_every_role_can_export(
    clients: dict[str, TestClient],
    role: str,
) -> None:
    response = clients[role].get("/api/invoices/export")

    assert response.status_code == 200
    assert csv_rows(response.text)[0] == EXPORT_HEADER
