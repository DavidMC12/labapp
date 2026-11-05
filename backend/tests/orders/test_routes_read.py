"""Tests for reading products, orders and the order list."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.orders.helpers import assert_field_error, assert_problem


def test_the_seeded_list_is_ordered_and_paged(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].get("/api/orders")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 7
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert [item["id"] for item in body["items"]] == [7, 6, 5, 4, 3, 2, 1]
    assert body["items"][0] == {
        "id": 7,
        "number": "PED-0007",
        "status": "confirmed",
        "customer_id": 3,
        "customer_name": "Cafetería La Esquina",
        "line_count": 2,
        "total": "55.28",
        "version": 1,
        "created_at": "2026-01-07T10:00:00Z",
        "updated_at": "2026-01-07T10:00:00Z",
    }


def test_a_page_beyond_the_last_is_empty(clients: dict[str, TestClient]) -> None:
    body = clients["sales"].get("/api/orders?page=2").json()

    assert body["items"] == []
    assert body["total"] == 7


@pytest.mark.parametrize(
    ("query", "expected_ids", "expected_total"),
    [
        ("status=draft", [1], 1),
        ("status=confirmed", [7, 3, 2], 3),
        ("customer_id=1", [1], 1),
        ("customer_id=2147483647", [], 0),
        ("q=cafeteria", [7], 1),
        ("q=PED-0001", [1], 1),
        ("q=ACME", [1], 1),
        ("q=%", [], 0),
        ("q=_", [], 0),
        ("q=%5C", [], 0),
    ],
)
def test_list_filters(
    clients: dict[str, TestClient],
    query: str,
    expected_ids: list[int],
    expected_total: int,
) -> None:
    body = clients["sales"].get(f"/api/orders?{query}").json()

    assert [item["id"] for item in body["items"]] == expected_ids
    assert body["total"] == expected_total


@pytest.mark.parametrize(
    ("query", "field", "code"),
    [
        ("page=abc", "page", "INVALID_FORMAT"),
        ("page=0", "page", "OUT_OF_RANGE"),
        ("page=1000001", "page", "OUT_OF_RANGE"),
        ("customer_id=abc", "customer_id", "INVALID_FORMAT"),
        ("customer_id=0", "customer_id", "OUT_OF_RANGE"),
        ("customer_id=2147483648", "customer_id", "OUT_OF_RANGE"),
        ("customer_id=1000000000000000000000000000000", "customer_id", "OUT_OF_RANGE"),
        ("status=lost", "status", "INVALID_FORMAT"),
    ],
)
def test_list_validation(clients: dict[str, TestClient], query: str, field: str, code: str) -> None:
    response = clients["sales"].get(f"/api/orders?{query}")

    body = assert_problem(response, 422, "VALIDATION_ERROR")
    assert [(error["field"], error["code"]) for error in body["errors"]] == [(field, code)]


def test_query_length_is_limited(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].get("/api/orders", params={"q": "a" * 101})

    assert_field_error(
        response,
        field="q",
        code="TOO_LONG",
        message="Debe tener como máximo 100 caracteres.",
    )


def test_query_with_a_control_character(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].get("/api/orders", params={"q": "acme\u0000"})

    assert_field_error(
        response,
        field="q",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )


def test_read_a_draft_with_its_line_and_totals(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].get("/api/orders/1")

    assert response.status_code == 200
    assert response.headers["etag"] == '"1"'
    assert response.json() == {
        "id": 1,
        "number": "PED-0001",
        "status": "draft",
        "customer": {"id": 1, "name": "Acme Industrial S.A.", "status": "active"},
        "lines": [
            {
                "id": 1,
                "product_id": 1,
                "sku": "KB-100",
                "name": "Teclado USB",
                "quantity": 2,
                "unit_price": "19.90",
                "line_total": "39.80",
            }
        ],
        "subtotal": "39.80",
        "tax_rate": "10.00",
        "tax": "3.98",
        "total": "43.78",
        "invoice_id": None,
        "version": 1,
        "created_at": "2026-01-01T10:00:00Z",
        "updated_at": "2026-01-01T10:00:00Z",
    }


def test_read_an_order_with_the_rounding_tie(clients: dict[str, TestClient]) -> None:
    body = clients["sales"].get("/api/orders/7").json()

    assert body["number"] == "PED-0007"
    assert body["subtotal"] == "50.25"
    assert body["tax"] == "5.03"
    assert body["total"] == "55.28"
    assert [line["id"] for line in body["lines"]] == [8, 9]


@pytest.mark.parametrize("order_id", [99, 0, 2_147_483_648])
def test_unknown_orders_are_not_found(clients: dict[str, TestClient], order_id: int) -> None:
    assert_problem(clients["sales"].get(f"/api/orders/{order_id}"), 404, "NOT_FOUND")


def test_a_non_integer_order_id_is_a_validation_error(
    clients: dict[str, TestClient],
) -> None:
    response = clients["sales"].get("/api/orders/abc")

    assert_field_error(
        response,
        field="id",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )


@pytest.mark.parametrize("role", ["admin", "sales", "finance", "readonly"])
def test_every_role_can_read_orders(clients: dict[str, TestClient], role: str) -> None:
    assert clients[role].get("/api/orders").status_code == 200
    assert clients[role].get("/api/orders/1").status_code == 200


def test_reads_require_a_session(app: FastAPI) -> None:
    client = TestClient(app)

    assert_problem(client.get("/api/products"), 401, "UNAUTHENTICATED")
    assert_problem(client.get("/api/settings"), 401, "UNAUTHENTICATED")
    assert_problem(client.get("/api/orders"), 401, "UNAUTHENTICATED")
    assert_problem(client.get("/api/orders/1"), 401, "UNAUTHENTICATED")
