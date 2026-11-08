"""Helpers shared by the invoice route tests."""

from __future__ import annotations

from typing import Any


def card_body(
    *,
    amount: str = "327.80",
    number: str = "4242 4242 4242 4242",
    expiry: str = "12/30",
    cvc: str = "123",
) -> dict[str, Any]:
    return {
        "method": "card",
        "amount": amount,
        "card": {"number": number, "expiry": expiry, "cvc": cvc},
    }


def transfer_body(
    *,
    amount: str = "327.80",
    reference: str = "TRF-2026-0001",
) -> dict[str, Any]:
    return {"method": "transfer", "amount": amount, "reference": reference}


def cash_body(*, amount: str = "327.80") -> dict[str, Any]:
    return {"method": "cash", "amount": amount}


def pay(
    client: Any,
    invoice_id: int,
    body: Any,
    *,
    key: str | None = "key-1",
    if_match: str | None = None,
) -> Any:
    headers: dict[str, str] = {}
    if key is not None:
        headers["Idempotency-Key"] = key
    if if_match is not None:
        headers["If-Match"] = if_match
    return client.post(f"/api/invoices/{invoice_id}/payments", json=body, headers=headers)


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


def field_codes(response: Any) -> list[tuple[str, str]]:
    body = assert_problem(response, 422, "VALIDATION_ERROR")
    return [(error["field"], error["code"]) for error in body["errors"]]
