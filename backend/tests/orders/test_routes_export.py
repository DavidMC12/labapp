"""Tests for the order CSV export route."""

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
from app.modules.customers.seed import seed_customers
from app.modules.orders.models import Order, OrderLine
from app.modules.orders.seed import seed_products
from tests.orders.helpers import assert_problem

EXPORT_HEADER = [
    "id",
    "number",
    "status",
    "customer_id",
    "customer_name",
    "subtotal",
    "tax_rate",
    "tax",
    "total",
    "invoice_id",
    "created_at",
    "updated_at",
]
BASE = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
STATUSES = (
    OrderStatus.DRAFT,
    OrderStatus.CONFIRMED,
    OrderStatus.PAID,
    OrderStatus.SHIPPED,
    OrderStatus.CANCELLED,
)
PRICE = Decimal("19.90")
TAX_RATE = Decimal("10.00")


def csv_rows(text: str) -> list[list[str]]:
    return list(csv.reader(StringIO(text)))


def many_orders() -> list[Order]:
    product = seed_products()[0]
    orders: list[Order] = []
    for identifier in range(1, 46):
        status = STATUSES[(identifier - 1) % len(STATUSES)]
        created_at = BASE + timedelta(minutes=identifier)
        orders.append(
            Order(
                id=identifier,
                number=f"PED-{identifier:04d}",
                status=status,
                customer_id=(identifier - 1) % 10 + 1,
                lines=(
                    OrderLine(
                        id=identifier,
                        product_id=product.id,
                        sku=product.sku,
                        name=product.name,
                        quantity=1,
                        unit_price=PRICE,
                    ),
                ),
                tax_rate=None if status == OrderStatus.DRAFT else TAX_RATE,
                version=1,
                created_at=created_at,
                updated_at=created_at,
                invoice_id=None,
            )
        )
    return orders


def replace_orders(app: FastAPI) -> None:
    app.state.customer_repository.replace_all(seed_customers())
    app.state.order_store.replace_all(seed_products(), many_orders(), TAX_RATE)


def exported_rows(response, header: list[str]) -> list[dict[str, str]]:
    rows = csv_rows(response.text)
    assert rows[0] == header
    return [dict(zip(header, row, strict=True)) for row in rows[1:]]


def test_the_export_has_the_header_and_every_row_of_the_list(
    app: FastAPI,
    clients: dict[str, TestClient],
) -> None:
    replace_orders(app)

    listed = clients["sales"].get("/api/orders")
    response = clients["sales"].get("/api/orders/export")

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
    replace_orders(app)

    ascending = clients["sales"].get(
        "/api/orders/export",
        params={"sort": "number", "direction": "asc"},
    )
    descending = clients["sales"].get(
        "/api/orders/export",
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
        {"q": "PED-0007"},
        {"status": "draft"},
        {"customer_id": 3},
        {"status": "draft", "customer_id": 1},
    ],
)
def test_the_export_reuses_the_list_filters(
    app: FastAPI,
    clients: dict[str, TestClient],
    params: dict[str, object],
) -> None:
    replace_orders(app)

    listed = clients["sales"].get("/api/orders", params=params)
    response = clients["sales"].get("/api/orders/export", params=params)

    assert listed.status_code == 200
    assert response.status_code == 200
    assert len(csv_rows(response.text)) - 1 == listed.json()["total"]


@pytest.mark.parametrize("page", [0, 2, 1_000_001])
def test_the_export_ignores_page(
    app: FastAPI,
    clients: dict[str, TestClient],
    page: int,
) -> None:
    replace_orders(app)

    response = clients["sales"].get("/api/orders/export", params={"page": page})

    assert response.status_code == 200
    assert len(csv_rows(response.text)) - 1 == 45


def test_the_export_headers_come_from_the_application_clock(
    clients: dict[str, TestClient],
    clock: OffsetClock,
) -> None:
    moved = clock.now() + timedelta(hours=2)
    clock.advance(timedelta(hours=2))
    try:
        response = clients["sales"].get("/api/orders/export")
    finally:
        clock.set_offset(timedelta(0))

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"] == (
        f'attachment; filename="orders-{moved:%Y%m%d}.csv"'
    )
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]


def test_the_export_requires_a_session(app: FastAPI) -> None:
    response = TestClient(app).get("/api/orders/export")

    assert_problem(response, 401, "UNAUTHENTICATED")


@pytest.mark.parametrize(
    "params",
    [{"status": "deleted"}, {"sort": "unknown"}, {"direction": "up"}],
)
def test_an_invalid_query_has_the_same_body_as_the_list(
    clients: dict[str, TestClient],
    params: dict[str, str],
) -> None:
    listed = clients["sales"].get("/api/orders", params=params)
    exported = clients["sales"].get("/api/orders/export", params=params)

    assert exported.status_code == listed.status_code == 422
    assert exported.json() == listed.json()


def test_a_draft_uses_the_computed_totals_of_the_list(
    clients: dict[str, TestClient],
) -> None:
    listed = clients["sales"].get("/api/orders")
    listed_row = next(item for item in listed.json()["items"] if item["number"] == "PED-0001")
    response = clients["sales"].get("/api/orders/export")
    rows = {row["number"]: row for row in exported_rows(response, EXPORT_HEADER)}

    assert rows["PED-0001"]["status"] == "draft"
    assert rows["PED-0001"]["subtotal"] == "39.80"
    assert rows["PED-0001"]["tax_rate"] == "10.00"
    assert rows["PED-0001"]["tax"] == "3.98"
    assert rows["PED-0001"]["total"] == listed_row["total"] == "43.78"
    assert rows["PED-0001"]["invoice_id"] == ""


@pytest.mark.parametrize("role", ["admin", "sales", "finance", "readonly"])
def test_every_role_can_export(
    clients: dict[str, TestClient],
    role: str,
) -> None:
    response = clients[role].get("/api/orders/export")

    assert response.status_code == 200
    assert csv_rows(response.text)[0] == EXPORT_HEADER
