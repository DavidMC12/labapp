"""Tests for creating customers."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.customers.helpers import (
    assert_field_error,
    assert_fields,
    assert_problem,
    create_payload,
)


@pytest.mark.parametrize("role", ["admin", "sales"])
def test_admin_and_sales_can_create(clients: dict[str, TestClient], role: str) -> None:
    response = clients[role].post(
        "/api/customers",
        json=create_payload(name="  Created Customer  ", email="  NEW@EXAMPLE.TEST  "),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 11
    assert body["name"] == "Created Customer"
    assert body["email"] == "new@example.test"
    assert body["status"] == "active"
    assert body["version"] == 1
    assert body["created_at"].endswith("Z")
    assert body["updated_at"] == body["created_at"]
    assert response.headers["location"] == "/api/customers/11"
    assert response.headers["etag"] == '"1"'


def test_create_with_a_duplicate_email_is_rejected(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].post(
        "/api/customers",
        json=create_payload(email="ACME@EXAMPLE.TEST"),
    )

    body = assert_problem(response, 409, "CUSTOMER_EMAIL_TAKEN")
    assert body["detail"] == "Ya existe un cliente con ese email."


def test_create_normalizes_address_line_breaks(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].post(
        "/api/customers",
        json=create_payload(address="Calle 1\r\nPiso 2"),
    )

    assert response.status_code == 201
    assert response.json()["address"] == "Calle 1\nPiso 2"


def test_create_reports_a_missing_name_and_a_bad_phone(
    clients: dict[str, TestClient],
) -> None:
    payload = create_payload(phone="abc")
    del payload["name"]

    response = clients["sales"].post("/api/customers", json=payload)

    assert_fields(
        response,
        [
            ("name", "REQUIRED"),
            ("phone", "INVALID_FORMAT"),
        ],
    )


@pytest.mark.parametrize("field", ["name", "email"])
def test_create_requires_name_and_email(
    clients: dict[str, TestClient],
    field: str,
) -> None:
    response = clients["sales"].post(
        "/api/customers",
        json=create_payload(**{field: "   "}),
    )

    assert_field_error(
        response,
        field=field,
        code="REQUIRED",
        message="Este campo es obligatorio.",
    )


def test_create_rejects_an_unknown_field(clients: dict[str, TestClient]) -> None:
    payload = create_payload()
    payload["status"] = "active"

    response = clients["sales"].post("/api/customers", json=payload)

    assert_field_error(
        response,
        field="status",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )


@pytest.mark.parametrize("role", ["finance", "readonly"])
def test_roles_without_customer_management_cannot_create(
    clients: dict[str, TestClient],
    role: str,
) -> None:
    response = clients[role].post("/api/customers", json=create_payload())

    body = assert_problem(response, 403, "FORBIDDEN")
    assert body["detail"] == "No tienes permiso para realizar esta acción."


def test_create_without_a_session_is_unauthenticated(app: FastAPI) -> None:
    client = TestClient(app)

    body = assert_problem(
        client.post("/api/customers", json=create_payload()),
        401,
        "UNAUTHENTICATED",
    )

    assert body["detail"] == "Inicia sesión para continuar."
