"""Tests for the customer CSV export route."""

from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from io import StringIO

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.infra.clock import OffsetClock
from app.modules.customers.models import Customer, CustomerStatus
from tests.customers.helpers import assert_field_error, assert_problem, create_payload

EXPORT_HEADER = [
    "id",
    "name",
    "email",
    "phone",
    "tax_id",
    "address",
    "status",
    "created_at",
    "updated_at",
]
BASE = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


def csv_rows(text: str) -> list[list[str]]:
    return list(csv.reader(StringIO(text)))


def many_customers() -> list[Customer]:
    return [
        Customer(
            id=identifier,
            name=f"Customer {identifier:02d}",
            email=f"customer{identifier:02d}@example.test",
            phone=None,
            tax_id=None,
            address=None,
            status=CustomerStatus.ACTIVE if identifier % 2 else CustomerStatus.INACTIVE,
            version=1,
            created_at=BASE + timedelta(minutes=identifier),
            updated_at=BASE + timedelta(minutes=identifier),
        )
        for identifier in range(1, 46)
    ]


def exported_ids(text: str) -> list[int]:
    return [int(row[0]) for row in csv_rows(text)[1:]]


def test_the_export_has_the_header_and_every_row_of_the_list(
    app: FastAPI,
    clients: dict[str, TestClient],
) -> None:
    app.state.customer_repository.replace_all(many_customers())

    listed = clients["sales"].get("/api/customers")
    response = clients["sales"].get("/api/customers/export")

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
    app.state.customer_repository.replace_all(many_customers())

    ascending = clients["sales"].get(
        "/api/customers/export",
        params={"sort": "name", "direction": "asc"},
    )
    descending = clients["sales"].get(
        "/api/customers/export",
        params={"sort": "name", "direction": "desc"},
    )

    assert exported_ids(ascending.text) == list(range(1, 46))
    assert exported_ids(descending.text) == list(range(45, 0, -1))


def test_the_export_reuses_the_list_filters(
    app: FastAPI,
    clients: dict[str, TestClient],
) -> None:
    app.state.customer_repository.replace_all(many_customers())
    params = {"q": "customer 1", "status": "active"}

    listed = clients["sales"].get("/api/customers", params=params)
    response = clients["sales"].get("/api/customers/export", params=params)

    assert listed.status_code == 200
    assert len(csv_rows(response.text)) - 1 == listed.json()["total"] == 5


@pytest.mark.parametrize("page", [0, 2, 1_000_001])
def test_the_export_ignores_page(
    app: FastAPI,
    clients: dict[str, TestClient],
    page: int,
) -> None:
    app.state.customer_repository.replace_all(many_customers())

    response = clients["sales"].get("/api/customers/export", params={"page": page})

    assert response.status_code == 200
    assert len(csv_rows(response.text)) - 1 == 45


def test_the_export_headers_come_from_the_application_clock(
    clients: dict[str, TestClient],
    clock: OffsetClock,
) -> None:
    moved = clock.now() + timedelta(hours=2)
    clock.advance(timedelta(hours=2))
    try:
        response = clients["sales"].get("/api/customers/export")
    finally:
        clock.set_offset(timedelta(0))

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"] == (
        f'attachment; filename="customers-{moved:%Y%m%d}.csv"'
    )
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]


def test_the_export_requires_a_session(app: FastAPI) -> None:
    response = TestClient(app).get("/api/customers/export")

    assert_problem(response, 401, "UNAUTHENTICATED")


def test_an_invalid_status_has_the_same_body_as_the_list(
    clients: dict[str, TestClient],
) -> None:
    listed = clients["sales"].get("/api/customers", params={"status": "deleted"})
    exported = clients["sales"].get("/api/customers/export", params={"status": "deleted"})

    assert exported.status_code == listed.status_code == 422
    assert exported.json() == listed.json()


def test_an_invalid_sort_has_the_same_body_as_the_list(
    clients: dict[str, TestClient],
) -> None:
    listed = clients["sales"].get("/api/customers", params={"sort": "unknown"})
    exported = clients["sales"].get("/api/customers/export", params={"sort": "unknown"})

    assert exported.status_code == listed.status_code == 422
    assert exported.json() == listed.json()


def test_a_formula_name_and_a_multiline_address_are_guarded(
    clients: dict[str, TestClient],
) -> None:
    created = clients["sales"].post(
        "/api/customers",
        json=create_payload(
            name='=HYPERLINK("http://x","y")',
            email="formula@example.test",
            address="Line 1\nLine 2",
        ),
    )
    assert created.status_code == 201

    response = clients["sales"].get("/api/customers/export")

    rows = csv_rows(response.text)
    records = [dict(zip(rows[0], row, strict=True)) for row in rows[1:]]
    record = next(item for item in records if item["email"] == "formula@example.test")
    assert record["name"] == '\'=HYPERLINK("http://x","y")'
    assert record["address"] == "Line 1\nLine 2"


def test_a_long_query_is_still_rejected(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].get(
        "/api/customers/export",
        params={"q": "a" * 101},
    )

    assert_field_error(
        response,
        field="q",
        code="TOO_LONG",
        message="Debe tener como máximo 100 caracteres.",
    )


@pytest.mark.parametrize("role", ["admin", "sales", "finance", "readonly"])
def test_every_role_can_export(
    clients: dict[str, TestClient],
    role: str,
) -> None:
    response = clients[role].get("/api/customers/export")

    assert response.status_code == 200
    assert csv_rows(response.text)[0] == EXPORT_HEADER
