"""Tests for the seeded catalog and orders."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

SEED_TOTALS = {
    1: ("draft", "39.80", "3.98", "43.78", [1]),
    2: ("confirmed", "110.00", "11.00", "121.00", [2, 3]),
    3: ("confirmed", "298.00", "29.80", "327.80", [4]),
    4: ("paid", "179.97", "18.00", "197.97", [5]),
    5: ("shipped", "699.00", "69.90", "768.90", [6]),
    6: ("cancelled", "109.60", "10.96", "120.56", [7]),
    7: ("confirmed", "50.25", "5.03", "55.28", [8, 9]),
}


@pytest.mark.parametrize(
    ("order_id", "expected"),
    SEED_TOTALS.items(),
)
def test_seed_order_totals_and_line_ids(
    clients: dict[str, TestClient],
    order_id: int,
    expected: tuple[str, str, str, str, list[int]],
) -> None:
    status, subtotal, tax, total, line_ids = expected

    body = clients["sales"].get(f"/api/orders/{order_id}").json()

    assert body["status"] == status
    assert body["subtotal"] == subtotal
    assert body["tax"] == tax
    assert body["total"] == total
    assert body["tax_rate"] == "10.00"
    assert body["invoice_id"] is None
    assert [line["id"] for line in body["lines"]] == line_ids


def test_the_seed_contains_the_fifteen_products(clients: dict[str, TestClient]) -> None:
    products = clients["sales"].get("/api/products").json()["items"]

    assert len(products) == 15
    assert products[6] == {
        "id": 7,
        "sku": "WC-720",
        "name": "Cámara web HD",
        "price": "34.50",
        "stock": 3,
    }
    assert products[8] == {
        "id": 9,
        "sku": "PR-400",
        "name": "Impresora láser",
        "price": "189.90",
        "stock": 0,
    }


def test_seed_numbers_continue_with_order_eight_and_line_ten(
    clients: dict[str, TestClient],
) -> None:
    created = clients["sales"].post("/api/orders", json={"customer_id": 1})
    added = clients["sales"].post(
        f"/api/orders/{created.json()['id']}/lines",
        json={"product_id": 1, "quantity": 2, "version": 1},
    )

    assert created.json()["number"] == "PED-0008"
    assert added.json()["lines"][0]["id"] == 10
