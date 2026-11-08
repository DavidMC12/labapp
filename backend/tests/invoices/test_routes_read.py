"""Tests for reading invoices and the seed links."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.invoices.helpers import assert_problem, field_codes


def test_the_seed_list_is_ordered_and_uses_the_summary_shape(
    clients: dict[str, TestClient],
) -> None:
    response = clients["finance"].get("/api/invoices")

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total"] == 3
    assert [item["id"] for item in body["items"]] == [3, 2, 1]
    assert body["items"][2] == {
        "id": 1,
        "number": "FAC-0001",
        "status": "issued",
        "order_id": 3,
        "order_number": "PED-0003",
        "customer_name": "Distribuidora Delta",
        "total": "327.80",
        "version": 1,
        "created_at": "2026-01-03T14:00:00Z",
        "updated_at": "2026-01-03T14:00:00Z",
    }


def test_the_list_filters_by_status_order_and_search(clients: dict[str, TestClient]) -> None:
    client = clients["finance"]

    issued = client.get("/api/invoices", params={"status": "issued"}).json()
    paid = client.get("/api/invoices", params={"status": "paid"}).json()
    by_order = client.get("/api/invoices", params={"order_id": 4}).json()
    by_number = client.get("/api/invoices", params={"q": "fac-0002"}).json()
    by_name = client.get("/api/invoices", params={"q": "iberica"}).json()

    assert [item["id"] for item in issued["items"]] == [1]
    assert [item["id"] for item in paid["items"]] == [3, 2]
    assert [item["id"] for item in by_order["items"]] == [2]
    assert [item["id"] for item in by_number["items"]] == [2]
    assert [item["id"] for item in by_name["items"]] == [3]


def test_the_list_pages(clients: dict[str, TestClient]) -> None:
    client = clients["finance"]

    first = client.get("/api/invoices", params={"page": 1}).json()
    second = client.get("/api/invoices", params={"page": 2}).json()

    assert first["total"] == 3
    assert [item["id"] for item in first["items"]] == [3, 2, 1]
    assert second["items"] == []
    assert second["total"] == 3


def test_an_invalid_status_is_a_field_error(clients: dict[str, TestClient]) -> None:
    response = clients["finance"].get("/api/invoices", params={"status": "lost"})

    assert field_codes(response) == [("status", "INVALID_FORMAT")]


@pytest.mark.parametrize("order_id", [0, 2_147_483_648])
def test_an_order_id_out_of_range_is_reported(
    clients: dict[str, TestClient],
    order_id: int,
) -> None:
    response = clients["finance"].get("/api/invoices", params={"order_id": order_id})

    assert field_codes(response) == [("order_id", "OUT_OF_RANGE")]


def test_an_invalid_page_and_a_long_query_are_reported(
    clients: dict[str, TestClient],
) -> None:
    page = clients["finance"].get("/api/invoices", params={"page": 0})
    query = clients["finance"].get("/api/invoices", params={"q": "x" * 101})

    assert field_codes(page) == [("page", "OUT_OF_RANGE")]
    assert field_codes(query) == [("q", "TOO_LONG")]


def test_one_invoice_carries_the_snapshot_the_lines_and_the_payments(
    clients: dict[str, TestClient],
) -> None:
    response = clients["finance"].get("/api/invoices/1")

    assert response.status_code == 200
    assert response.headers["etag"] == '"1"'
    body = response.json()
    assert body == {
        "id": 1,
        "number": "FAC-0001",
        "status": "issued",
        "order_id": 3,
        "order_number": "PED-0003",
        "customer": {
            "id": 4,
            "name": "Distribuidora Delta",
            "tax_id": "DELT-700789",
            "address": None,
        },
        "lines": [
            {
                "id": 1,
                "product_id": 3,
                "sku": "MN-240",
                "name": 'Monitor 24"',
                "quantity": 2,
                "unit_price": "149.00",
                "line_total": "298.00",
            }
        ],
        "subtotal": "298.00",
        "tax_rate": "10.00",
        "tax": "29.80",
        "total": "327.80",
        "payments": [
            {
                "id": 1,
                "method": "card",
                "status": "declined",
                "amount": "327.80",
                "reference": None,
                "card_last4": "0002",
                "reason": "CARD_DECLINED",
                "created_at": "2026-01-03T15:00:00Z",
            },
            {
                "id": 2,
                "method": "card",
                "status": "failed",
                "amount": "327.80",
                "reference": None,
                "card_last4": "0003",
                "reason": "GATEWAY_UNAVAILABLE",
                "created_at": "2026-01-03T15:00:00Z",
            },
        ],
        "version": 1,
        "created_at": "2026-01-03T14:00:00Z",
        "updated_at": "2026-01-03T14:00:00Z",
    }


def test_an_unknown_invoice_is_not_found(clients: dict[str, TestClient]) -> None:
    assert_problem(clients["finance"].get("/api/invoices/99"), 404, "NOT_FOUND")


def test_every_role_can_read_invoices(clients: dict[str, TestClient]) -> None:
    for client in clients.values():
        assert client.get("/api/invoices").status_code == 200
        assert client.get("/api/invoices/1").status_code == 200


def test_a_request_without_a_session_is_unauthenticated(app) -> None:
    from fastapi.testclient import TestClient

    response = TestClient(app).get("/api/invoices")

    assert response.status_code == 401


def test_the_seeded_orders_keep_their_version_and_timestamps(
    clients: dict[str, TestClient],
) -> None:
    for order_id, invoice_id in ((3, 1), (4, 2), (5, 3)):
        body = clients["finance"].get(f"/api/orders/{order_id}").json()
        assert body["invoice_id"] == invoice_id
        assert body["version"] == 1
        assert body["updated_at"] == body["created_at"]


def test_cancelling_a_confirmed_order_voids_its_invoice(
    clients: dict[str, TestClient],
) -> None:
    cancelled = clients["sales"].post("/api/orders/3/cancel")

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    invoice = clients["finance"].get("/api/invoices/1").json()
    assert invoice["status"] == "void"
    assert invoice["version"] == 2
