"""Tests for reading customers."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.customers.helpers import assert_field_error, assert_problem


@pytest.mark.parametrize("role", ["admin", "sales", "finance", "readonly"])
def test_every_role_can_read_customers(clients: dict[str, TestClient], role: str) -> None:
    listing = clients[role].get("/api/customers")
    detail = clients[role].get("/api/customers/1")

    assert listing.status_code == 200
    assert detail.status_code == 200
    assert detail.json()["email"] == "acme@example.test"
    assert detail.headers["etag"] == '"1"'


def test_read_returns_the_customer_shape(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].get("/api/customers/1")

    assert response.json() == {
        "id": 1,
        "name": "Acme Industrial S.A.",
        "email": "acme@example.test",
        "phone": "+1 555 010 0001",
        "tax_id": "ACME-900123",
        "address": "Av. Principal 100",
        "status": "active",
        "version": 1,
        "created_at": "2026-01-01T09:01:00Z",
        "updated_at": "2026-01-01T09:01:00Z",
    }


def test_read_without_a_session_is_unauthenticated(
    app: FastAPI,
) -> None:
    client = TestClient(app)

    body = assert_problem(client.get("/api/customers"), 401, "UNAUTHENTICATED")

    assert body["detail"] == "Inicia sesión para continuar."


def test_read_unknown_id_is_not_found(clients: dict[str, TestClient]) -> None:
    body = assert_problem(clients["sales"].get("/api/customers/99"), 404, "NOT_FOUND")

    assert body["detail"] == "No se encontró el recurso solicitado."


@pytest.mark.parametrize("customer_id", [0, 2_147_483_648])
def test_read_out_of_range_id_is_not_found(
    clients: dict[str, TestClient],
    customer_id: int,
) -> None:
    assert_problem(clients["sales"].get(f"/api/customers/{customer_id}"), 404, "NOT_FOUND")


def test_read_non_integer_id_is_a_validation_error(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].get("/api/customers/not-an-integer")

    assert_field_error(
        response,
        field="id",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )
