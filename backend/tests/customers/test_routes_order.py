"""Tests for the order of the checks on customer writes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.customers.helpers import assert_problem, create_payload


def test_permission_is_checked_before_unknown_id_and_body(
    clients: dict[str, TestClient],
) -> None:
    response = clients["finance"].patch(
        "/api/customers/999",
        json={"name": None, "version": 0},
    )

    assert_problem(response, 403, "FORBIDDEN")


def test_permission_is_checked_before_unknown_id_and_a_pydantic_body_error(
    clients: dict[str, TestClient],
) -> None:
    response = clients["finance"].patch(
        "/api/customers/999",
        json={"name": "Missing version"},
    )

    assert_problem(response, 403, "FORBIDDEN")


def test_create_checks_permission_before_body(clients: dict[str, TestClient]) -> None:
    payload = create_payload(phone="abc")
    del payload["name"]

    assert_problem(
        clients["readonly"].post("/api/customers", json=payload),
        403,
        "FORBIDDEN",
    )


def test_unknown_id_is_checked_before_an_invalid_body(
    clients: dict[str, TestClient],
) -> None:
    response = clients["sales"].patch(
        "/api/customers/999",
        json={"name": None, "version": 0},
    )

    assert_problem(response, 404, "NOT_FOUND")


def test_unknown_id_is_checked_before_a_pydantic_body_error(
    clients: dict[str, TestClient],
) -> None:
    response = clients["sales"].patch(
        "/api/customers/999",
        json={"name": "Missing version"},
    )

    assert_problem(response, 404, "NOT_FOUND")


def test_existing_id_with_an_invalid_body_is_a_validation_error(
    clients: dict[str, TestClient],
) -> None:
    response = clients["sales"].patch(
        "/api/customers/1",
        json={"name": None, "version": 1},
    )

    body = assert_problem(response, 422, "VALIDATION_ERROR")
    assert body["errors"] == [
        {
            "field": "name",
            "code": "REQUIRED",
            "message": "Este campo es obligatorio.",
        }
    ]


def test_existing_id_with_a_pydantic_body_error(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].patch(
        "/api/customers/1",
        json={"name": "Missing version"},
    )

    body = assert_problem(response, 422, "VALIDATION_ERROR")
    assert body["errors"] == [
        {
            "field": "version",
            "code": "REQUIRED",
            "message": "Este campo es obligatorio.",
        }
    ]


def test_unknown_id_is_checked_before_a_stale_if_match(
    clients: dict[str, TestClient],
) -> None:
    response = clients["sales"].post(
        "/api/customers/999/deactivate",
        headers={"If-Match": '"1"'},
    )

    assert_problem(response, 404, "NOT_FOUND")


def test_unknown_id_is_checked_before_a_malformed_if_match(
    clients: dict[str, TestClient],
) -> None:
    response = clients["sales"].post(
        "/api/customers/999/reactivate",
        headers={"If-Match": "not-a-version"},
    )

    assert_problem(response, 404, "NOT_FOUND")
