"""Tests for patching customers."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.customers.helpers import assert_field_error, assert_problem


def test_patch_a_single_field_bumps_the_version(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].patch(
        "/api/customers/1",
        json={"name": "Acme Updated", "version": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Acme Updated"
    assert body["email"] == "acme@example.test"
    assert body["tax_id"] == "ACME-900123"
    assert body["version"] == 2
    assert body["updated_at"].endswith("Z")
    assert response.headers["etag"] == '"2"'


def test_patch_null_clears_optional_fields(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].patch(
        "/api/customers/1",
        json={"phone": None, "tax_id": None, "address": None, "version": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["phone"] is None
    assert body["tax_id"] is None
    assert body["address"] is None
    assert body["version"] == 2


@pytest.mark.parametrize("field", ["name", "email"])
def test_patch_null_for_required_fields(
    clients: dict[str, TestClient],
    field: str,
) -> None:
    response = clients["sales"].patch(
        "/api/customers/1",
        json={field: None, "version": 1},
    )

    assert_field_error(
        response,
        field=field,
        code="REQUIRED",
        message="Este campo es obligatorio.",
    )


def test_patch_missing_version_is_required(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].patch(
        "/api/customers/1",
        json={"name": "Acme Updated"},
    )

    assert_field_error(
        response,
        field="version",
        code="REQUIRED",
        message="Este campo es obligatorio.",
    )


def test_patch_version_zero_is_out_of_range(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].patch(
        "/api/customers/1",
        json={"name": "Acme Updated", "version": 0},
    )

    assert_field_error(
        response,
        field="version",
        code="OUT_OF_RANGE",
        message="El valor debe estar entre 1 y 2147483647.",
    )


def test_patch_with_a_stale_version_is_a_conflict(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].patch(
        "/api/customers/1",
        json={"name": "Acme Updated", "version": 2},
    )

    body = assert_problem(response, 409, "VERSION_CONFLICT")
    assert body["detail"] == (
        "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo."
    )


def test_patch_email_to_another_customers_email_is_taken(
    clients: dict[str, TestClient],
) -> None:
    response = clients["sales"].patch(
        "/api/customers/1",
        json={"email": "BETA@EXAMPLE.TEST", "version": 1},
    )

    body = assert_problem(response, 409, "CUSTOMER_EMAIL_TAKEN")
    assert body["detail"] == "Ya existe un cliente con ese email."


def test_patch_rejects_an_unknown_field(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].patch(
        "/api/customers/1",
        json={"status": "inactive", "version": 1},
    )

    assert_field_error(
        response,
        field="status",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )


def test_patch_without_real_changes_keeps_the_version(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].patch(
        "/api/customers/1",
        json={"name": "Acme Industrial S.A.", "version": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 1
    assert body["updated_at"] == "2026-01-01T09:01:00Z"
    assert response.headers["etag"] == '"1"'


@pytest.mark.parametrize("role", ["finance", "readonly"])
def test_roles_without_customer_management_cannot_patch(
    clients: dict[str, TestClient],
    role: str,
) -> None:
    response = clients[role].patch(
        "/api/customers/1",
        json={"name": "Acme Updated", "version": 1},
    )

    assert_problem(response, 403, "FORBIDDEN")


def test_patch_without_a_session_is_unauthenticated(app: FastAPI) -> None:
    client = TestClient(app)

    assert_problem(
        client.patch("/api/customers/1", json={"name": "Acme Updated", "version": 1}),
        401,
        "UNAUTHENTICATED",
    )
