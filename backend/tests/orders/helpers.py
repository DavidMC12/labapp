"""Helpers shared by the order route tests."""

from __future__ import annotations

from typing import Any


def create_order_payload(customer_id: int | None = 1) -> dict[str, Any]:
    return {"customer_id": customer_id}


def change_customer_payload(
    customer_id: int | None = 1,
    version: int | None = 1,
) -> dict[str, Any]:
    return {"customer_id": customer_id, "version": version}


def add_line_payload(
    product_id: int | None = 1,
    quantity: int | None = 1,
    version: int | None = 1,
) -> dict[str, Any]:
    return {"product_id": product_id, "quantity": quantity, "version": version}


def quantity_payload(
    quantity: int | None = 1,
    version: int | None = 1,
) -> dict[str, Any]:
    return {"quantity": quantity, "version": version}


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


def create_order(client: Any, customer_id: int = 1) -> Any:
    response = client.post("/api/orders", json=create_order_payload(customer_id))
    assert response.status_code == 201
    return response
