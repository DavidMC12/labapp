"""Helpers shared by the customer route tests."""

from __future__ import annotations

from typing import Any

CUSTOMER = {
    "name": "New Customer",
    "email": "new.customer@example.test",
    "phone": None,
    "tax_id": None,
    "address": None,
}


def create_payload(**overrides: Any) -> dict[str, Any]:
    return {**CUSTOMER, **overrides}


def assert_problem(response: Any, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["status"] == status
    assert body["code"] == code
    return body


def assert_field_error(
    response: Any,
    *,
    field: str,
    code: str,
    message: str,
) -> None:
    body = assert_problem(response, 422, "VALIDATION_ERROR")
    assert body["detail"] == "Revisa los datos ingresados."
    assert body["errors"] == [{"field": field, "code": code, "message": message}]


def assert_fields(response: Any, expected: list[tuple[str, str]]) -> None:
    body = assert_problem(response, 422, "VALIDATION_ERROR")
    assert [(error["field"], error["code"]) for error in body["errors"]] == expected
