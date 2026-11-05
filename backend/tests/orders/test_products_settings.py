"""Tests for products and settings."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.orders.helpers import assert_field_error, assert_problem


@pytest.mark.parametrize("role", ["admin", "sales", "finance", "readonly"])
def test_products_are_readable_by_every_role(clients: dict[str, TestClient], role: str) -> None:
    response = clients[role].get("/api/products")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 15
    assert [item["id"] for item in items] == list(range(1, 16))
    assert items[0] == {
        "id": 1,
        "sku": "KB-100",
        "name": "Teclado USB",
        "price": "19.90",
        "stock": 120,
    }


@pytest.mark.parametrize("role", ["admin", "sales", "finance", "readonly"])
def test_settings_are_readable_by_every_role(clients: dict[str, TestClient], role: str) -> None:
    response = clients[role].get("/api/settings")

    assert response.status_code == 200
    assert response.json() == {"tax_rate": "10.00"}


def test_only_admin_can_change_the_tax_rate(clients: dict[str, TestClient]) -> None:
    response = clients["admin"].patch("/api/settings", json={"tax_rate": "7"})

    assert response.status_code == 200
    assert response.json() == {"tax_rate": "7.00"}

    for role in ("sales", "finance", "readonly"):
        assert_problem(
            clients[role].patch("/api/settings", json={"tax_rate": "8"}),
            403,
            "FORBIDDEN",
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [("0", "0.00"), ("0.00", "0.00"), ("100", "100.00"), ("7", "7.00")],
)
def test_valid_tax_rates_are_stored_with_two_decimals(
    clients: dict[str, TestClient], value: str, expected: str
) -> None:
    response = clients["admin"].patch("/api/settings", json={"tax_rate": value})

    assert response.status_code == 200
    assert response.json() == {"tax_rate": expected}
    assert clients["admin"].get("/api/settings").json() == {"tax_rate": expected}


@pytest.mark.parametrize(
    "value",
    ["", " 7", "1e1", "10.123", "-1", "abc", 10],
)
def test_invalid_tax_rate_formats(clients: dict[str, TestClient], value: object) -> None:
    response = clients["admin"].patch("/api/settings", json={"tax_rate": value})

    assert_field_error(
        response,
        field="tax_rate",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )


@pytest.mark.parametrize("value", ["100.01", "101", "999"])
def test_tax_rate_out_of_range(clients: dict[str, TestClient], value: str) -> None:
    response = clients["admin"].patch("/api/settings", json={"tax_rate": value})

    assert_field_error(
        response,
        field="tax_rate",
        code="OUT_OF_RANGE",
        message="El valor debe estar entre 0 y 100.",
    )


def test_tax_rate_is_required(clients: dict[str, TestClient]) -> None:
    response = clients["admin"].patch("/api/settings", json={})

    assert_field_error(
        response,
        field="tax_rate",
        code="REQUIRED",
        message="Este campo es obligatorio.",
    )


def test_settings_reject_unknown_fields(clients: dict[str, TestClient]) -> None:
    response = clients["admin"].patch("/api/settings", json={"tax_rate": "10", "unknown": 1})

    assert_field_error(
        response,
        field="unknown",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )


def test_settings_require_a_session(clients: dict[str, TestClient]) -> None:
    assert_problem(TestClient(clients["admin"].app).get("/api/settings"), 401, "UNAUTHENTICATED")
