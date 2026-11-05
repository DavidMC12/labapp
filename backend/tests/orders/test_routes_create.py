"""Tests for creating orders."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.orders.helpers import (
    assert_field_error,
    assert_problem,
    create_order_payload,
)


@pytest.mark.parametrize("role", ["admin", "sales"])
def test_admin_and_sales_can_create_a_draft(clients: dict[str, TestClient], role: str) -> None:
    response = clients[role].post("/api/orders", json=create_order_payload(1))

    assert response.status_code == 201
    assert response.headers["location"] == "/api/orders/8"
    assert response.headers["etag"] == '"1"'
    body = response.json()
    assert body["id"] == 8
    assert body["number"] == "PED-0008"
    assert body["status"] == "draft"
    assert body["customer"] == {
        "id": 1,
        "name": "Acme Industrial S.A.",
        "status": "active",
    }
    assert body["lines"] == []
    assert body["subtotal"] == "0.00"
    assert body["tax_rate"] == "10.00"
    assert body["tax"] == "0.00"
    assert body["total"] == "0.00"
    assert body["invoice_id"] is None
    assert body["version"] == 1
    assert body["created_at"] == body["updated_at"]
    assert body["created_at"].endswith("Z")


def test_created_orders_continue_the_number_sequence(clients: dict[str, TestClient]) -> None:
    first = clients["sales"].post("/api/orders", json=create_order_payload(1))
    second = clients["sales"].post("/api/orders", json=create_order_payload(2))

    assert first.json()["number"] == "PED-0008"
    assert second.json()["number"] == "PED-0009"
    assert first.json()["id"] == 8
    assert second.json()["id"] == 9


@pytest.mark.parametrize("role", ["finance", "readonly"])
def test_other_roles_cannot_create(clients: dict[str, TestClient], role: str) -> None:
    assert_problem(
        clients[role].post("/api/orders", json=create_order_payload(1)),
        403,
        "FORBIDDEN",
    )


def test_creating_requires_a_session(app: FastAPI) -> None:
    assert_problem(
        TestClient(app).post("/api/orders", json=create_order_payload(1)),
        401,
        "UNAUTHENTICATED",
    )


def test_an_inactive_customer_is_rejected(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].post("/api/orders", json=create_order_payload(5))

    body = assert_problem(response, 422, "CUSTOMER_INACTIVE")
    assert body["detail"] == "El cliente está desactivado y no puede recibir pedidos."


@pytest.mark.parametrize("customer_id", [99, 0, 2_147_483_648])
def test_an_unknown_or_out_of_range_customer_is_an_unknown_reference(
    clients: dict[str, TestClient], customer_id: int
) -> None:
    response = clients["sales"].post("/api/orders", json=create_order_payload(customer_id))

    assert_field_error(
        response,
        field="customer_id",
        code="REFERENCE_NOT_FOUND",
        message="El registro indicado no existe.",
    )


def test_customer_id_is_required(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].post("/api/orders", json={})

    assert_field_error(
        response,
        field="customer_id",
        code="REQUIRED",
        message="Este campo es obligatorio.",
    )


@pytest.mark.parametrize("customer_id", ["5", 5.0, True])
def test_customer_id_is_strict(clients: dict[str, TestClient], customer_id: object) -> None:
    response = clients["sales"].post("/api/orders", json={"customer_id": customer_id})

    assert_field_error(
        response,
        field="customer_id",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )


def test_unknown_fields_are_rejected(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].post("/api/orders", json={"customer_id": 1, "unknown": True})

    assert_field_error(
        response,
        field="unknown",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )
