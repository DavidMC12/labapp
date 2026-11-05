"""Tests for deactivating and reactivating customers."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.customers.helpers import assert_problem


@pytest.mark.parametrize("role", ["admin", "sales"])
def test_deactivate_then_reactivate(clients: dict[str, TestClient], role: str) -> None:
    deactivated = clients[role].post(
        "/api/customers/1/deactivate",
        headers={"If-Match": '"1"'},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "inactive"
    assert deactivated.json()["version"] == 2
    assert deactivated.headers["etag"] == '"2"'

    reactivated = clients[role].post(
        "/api/customers/1/reactivate",
        headers={"If-Match": "2"},
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "active"
    assert reactivated.json()["version"] == 3
    assert reactivated.headers["etag"] == '"3"'


def test_reactivate_an_inactive_seed_customer(clients: dict[str, TestClient]) -> None:
    response = clients["admin"].post(
        "/api/customers/5/reactivate",
        headers={"If-Match": '"1"'},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "active"
    assert response.json()["version"] == 2


def test_repeating_the_same_state_is_idempotent(clients: dict[str, TestClient]) -> None:
    first = clients["sales"].post(
        "/api/customers/1/deactivate",
        headers={"If-Match": '"1"'},
    )
    assert first.status_code == 200

    second = clients["sales"].post(
        "/api/customers/1/deactivate",
        headers={"If-Match": '"2"'},
    )
    third = clients["sales"].post("/api/customers/1/deactivate")

    assert second.status_code == 200
    assert second.json()["status"] == "inactive"
    assert second.json()["version"] == 2
    assert third.status_code == 200
    assert third.json()["version"] == 2


def test_stale_if_match_wins_even_when_the_state_already_matches(
    clients: dict[str, TestClient],
) -> None:
    first = clients["sales"].post(
        "/api/customers/1/deactivate",
        headers={"If-Match": '"1"'},
    )
    assert first.status_code == 200

    body = assert_problem(
        clients["sales"].post(
            "/api/customers/1/deactivate",
            headers={"If-Match": '"1"'},
        ),
        409,
        "VERSION_CONFLICT",
    )
    assert body["detail"] == (
        "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo."
    )


def test_stale_if_match_on_an_already_active_customer(
    clients: dict[str, TestClient],
) -> None:
    assert_problem(
        clients["sales"].post(
            "/api/customers/1/reactivate",
            headers={"If-Match": '"99"'},
        ),
        409,
        "VERSION_CONFLICT",
    )


@pytest.mark.parametrize("value", ["abc", '"3', '3"', '"3.0"', '""', ""])
def test_malformed_if_match_is_a_validation_error(
    clients: dict[str, TestClient],
    value: str,
) -> None:
    response = clients["sales"].post(
        "/api/customers/1/deactivate",
        headers={"If-Match": value},
    )

    body = assert_problem(response, 422, "VALIDATION_ERROR")
    assert body["errors"] == [
        {
            "field": "If-Match",
            "code": "INVALID_FORMAT",
            "message": "El formato no es válido.",
        }
    ]


@pytest.mark.parametrize("action", ["deactivate", "reactivate"])
@pytest.mark.parametrize("value", ["9" * 5000, "9" * 11])
def test_a_long_if_match_is_a_validation_error_without_an_integer_conversion(
    clients: dict[str, TestClient],
    action: str,
    value: str,
) -> None:
    response = clients["sales"].post(
        f"/api/customers/1/{action}",
        headers={"If-Match": value},
    )

    body = assert_problem(response, 422, "VALIDATION_ERROR")
    assert body["errors"] == [
        {
            "field": "If-Match",
            "code": "INVALID_FORMAT",
            "message": "El formato no es válido.",
        }
    ]


@pytest.mark.parametrize("action", ["deactivate", "reactivate"])
def test_the_quoted_maximum_version_reaches_the_version_check(
    clients: dict[str, TestClient],
    action: str,
) -> None:
    response = clients["sales"].post(
        f"/api/customers/1/{action}",
        headers={"If-Match": '"2147483647"'},
    )

    assert_problem(response, 409, "VERSION_CONFLICT")


@pytest.mark.parametrize("role", ["finance", "readonly"])
@pytest.mark.parametrize("action", ["deactivate", "reactivate"])
def test_roles_without_customer_management_cannot_change_status(
    clients: dict[str, TestClient],
    role: str,
    action: str,
) -> None:
    response = clients[role].post(f"/api/customers/1/{action}")

    assert_problem(response, 403, "FORBIDDEN")


@pytest.mark.parametrize("action", ["deactivate", "reactivate"])
def test_status_change_without_a_session_is_unauthenticated(
    app: FastAPI,
    action: str,
) -> None:
    client = TestClient(app)

    assert_problem(client.post(f"/api/customers/1/{action}"), 401, "UNAUTHENTICATED")
