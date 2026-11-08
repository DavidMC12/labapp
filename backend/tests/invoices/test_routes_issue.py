"""Tests for issuing invoices."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.modules.customers.models import CustomerStatus
from tests.invoices.helpers import assert_problem, field_codes


def test_finance_issues_the_invoice_of_order_two(clients: dict[str, TestClient]) -> None:
    response = clients["finance"].post("/api/orders/2/invoice")

    assert response.status_code == 201
    assert response.headers["location"] == "/api/invoices/4"
    assert response.headers["etag"] == '"1"'
    body = response.json()
    assert body["id"] == 4
    assert body["number"] == "FAC-0004"
    assert body["lines"][0]["id"] == 4
    assert body["lines"][1]["id"] == 5
    assert body["total"] == "121.00"
    order = clients["finance"].get("/api/orders/2").json()
    assert order["invoice_id"] == 4
    assert order["version"] == 2


def test_admin_can_issue(clients: dict[str, TestClient]) -> None:
    assert clients["admin"].post("/api/orders/2/invoice").status_code == 201


@pytest.mark.parametrize("role", ["sales", "readonly"])
def test_other_roles_cannot_issue(clients: dict[str, TestClient], role: str) -> None:
    assert_problem(clients[role].post("/api/orders/2/invoice"), 403, "FORBIDDEN")


def test_a_wrong_role_with_an_unknown_order_is_forbidden(clients: dict[str, TestClient]) -> None:
    assert_problem(clients["sales"].post("/api/orders/99/invoice"), 403, "FORBIDDEN")


def test_an_unknown_order_is_not_found(clients: dict[str, TestClient]) -> None:
    assert_problem(clients["finance"].post("/api/orders/99/invoice"), 404, "NOT_FOUND")


def test_a_stale_if_match_is_a_conflict(clients: dict[str, TestClient]) -> None:
    response = clients["finance"].post(
        "/api/orders/2/invoice",
        headers={"If-Match": '"9"'},
    )

    assert_problem(response, 409, "VERSION_CONFLICT")


@pytest.mark.parametrize("value", ["abc", '"1', "1" * 11])
def test_a_malformed_if_match_is_a_field_error(
    clients: dict[str, TestClient],
    value: str,
) -> None:
    response = clients["finance"].post(
        "/api/orders/2/invoice",
        headers={"If-Match": value},
    )

    assert field_codes(response) == [("If-Match", "INVALID_FORMAT")]


def test_an_already_invoiced_order_is_a_conflict(clients: dict[str, TestClient]) -> None:
    assert_problem(
        clients["finance"].post("/api/orders/3/invoice"),
        409,
        "INVOICE_ALREADY_EXISTS",
    )


def test_a_draft_cannot_be_invoiced(clients: dict[str, TestClient]) -> None:
    assert_problem(
        clients["finance"].post("/api/orders/1/invoice"),
        409,
        "ORDER_NOT_INVOICEABLE",
    )


def test_a_customer_without_tax_id_cannot_be_invoiced(clients: dict[str, TestClient]) -> None:
    assert_problem(
        clients["finance"].post("/api/orders/7/invoice"),
        422,
        "CUSTOMER_TAX_ID_REQUIRED",
    )


def test_a_confirmed_order_of_an_inactive_customer_can_be_invoiced(
    app,
    clients: dict[str, TestClient],
) -> None:
    app.state.customer_repository.set_status(
        2,
        CustomerStatus.INACTIVE,
        None,
        datetime(2026, 11, 5, 15, 0, tzinfo=UTC),
    )

    assert clients["finance"].post("/api/orders/2/invoice").status_code == 201


def test_the_notice_is_logged_once_per_invoice(
    clients: dict[str, TestClient],
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="app.modules.invoices.mail"):
        assert clients["finance"].post("/api/orders/2/invoice").status_code == 201

    messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "app.modules.invoices.mail"
    ]
    assert messages == ["Factura FAC-0004 emitida"]
    assert "beta@example.test" not in caplog.text
