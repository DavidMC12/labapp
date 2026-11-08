"""Tests for the shared invoice and payment rules."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

import pytest

from app.domain.orders import OrderStatus
from app.errors import ApiError
from app.modules.invoices.models import InvoiceStatus
from app.modules.invoices.rules import (
    CUSTOMER_TAX_ID_REQUIRED_MESSAGE,
    IDEMPOTENCY_KEY_REUSED_MESSAGE,
    INVOICE_ALREADY_EXISTS_MESSAGE,
    INVOICE_NOT_PAYABLE_MESSAGE,
    ORDER_NOT_INVOICEABLE_MESSAGE,
    PAYMENT_AMOUNT_MISMATCH_MESSAGE,
    PAYMENT_DECLINED_MESSAGE,
    PAYMENT_GATEWAY_UNAVAILABLE_MESSAGE,
    amount_mismatch,
    customer_tax_id_required,
    ensure_amount,
    ensure_can_invoice,
    ensure_payable,
    gateway_unavailable,
    invoice_already_exists,
    invoice_not_payable,
    key_reused,
    order_not_invoiceable,
    payment_declined,
    totals_for,
)


def _raised(call: Callable[[], object]) -> ApiError:
    with pytest.raises(ApiError) as error:
        call()
    return error.value


def test_invoice_already_exists_wins_over_the_other_checks() -> None:
    error = _raised(
        lambda: ensure_can_invoice(OrderStatus.DRAFT, True, None),
    )

    assert error.status == 409
    assert error.code == "INVOICE_ALREADY_EXISTS"
    assert error.detail == INVOICE_ALREADY_EXISTS_MESSAGE


def test_order_not_invoiceable_comes_before_the_tax_id() -> None:
    error = _raised(
        lambda: ensure_can_invoice(OrderStatus.DRAFT, False, None),
    )

    assert error.status == 409
    assert error.code == "ORDER_NOT_INVOICEABLE"
    assert error.detail == ORDER_NOT_INVOICEABLE_MESSAGE


@pytest.mark.parametrize("tax_id", [None, ""])
def test_customer_tax_id_is_required(tax_id: str | None) -> None:
    error = _raised(
        lambda: ensure_can_invoice(OrderStatus.CONFIRMED, False, tax_id),
    )

    assert error.status == 422
    assert error.code == "CUSTOMER_TAX_ID_REQUIRED"
    assert error.detail == CUSTOMER_TAX_ID_REQUIRED_MESSAGE


def test_a_confirmed_order_without_invoice_and_with_tax_id_is_invoiceable() -> None:
    ensure_can_invoice(OrderStatus.CONFIRMED, False, "ACME-900123")


@pytest.mark.parametrize("status", [InvoiceStatus.PAID, InvoiceStatus.VOID])
def test_only_an_issued_invoice_is_payable(status: InvoiceStatus) -> None:
    error = _raised(lambda: ensure_payable(status))

    assert error.status == 409
    assert error.code == "INVOICE_NOT_PAYABLE"
    assert error.detail == INVOICE_NOT_PAYABLE_MESSAGE


def test_an_issued_invoice_is_payable() -> None:
    ensure_payable(InvoiceStatus.ISSUED)


@pytest.mark.parametrize(
    ("amount", "total"),
    [
        (Decimal("327.80"), Decimal("327.80")),
        (Decimal("327.8"), Decimal("327.80")),
        (Decimal("121.004"), Decimal("121.00")),
    ],
)
def test_a_full_payment_matches_the_total(amount: Decimal, total: Decimal) -> None:
    ensure_amount(amount, total)


def test_another_amount_is_a_mismatch() -> None:
    error = _raised(lambda: ensure_amount(Decimal("327.81"), Decimal("327.80")))

    assert error.status == 422
    assert error.code == "PAYMENT_AMOUNT_MISMATCH"
    assert error.detail == PAYMENT_AMOUNT_MISMATCH_MESSAGE


def test_key_reused_error() -> None:
    error = key_reused()

    assert error.status == 422
    assert error.code == "IDEMPOTENCY_KEY_REUSED"
    assert error.detail == IDEMPOTENCY_KEY_REUSED_MESSAGE


def test_payment_declined_carries_the_payment_and_reason() -> None:
    error = payment_declined(5, "CARD_DECLINED")

    assert error.status == 402
    assert error.code == "PAYMENT_DECLINED"
    assert error.detail == PAYMENT_DECLINED_MESSAGE
    assert error.extra == {"payment_id": 5, "reason": "CARD_DECLINED"}


def test_gateway_unavailable_carries_the_payment_and_reason() -> None:
    error = gateway_unavailable(6, "GATEWAY_UNAVAILABLE")

    assert error.status == 503
    assert error.code == "PAYMENT_GATEWAY_UNAVAILABLE"
    assert error.detail == PAYMENT_GATEWAY_UNAVAILABLE_MESSAGE
    assert error.extra == {"payment_id": 6, "reason": "GATEWAY_UNAVAILABLE"}


def test_the_named_error_builders_match_the_ensure_functions() -> None:
    assert invoice_already_exists().code == "INVOICE_ALREADY_EXISTS"
    assert order_not_invoiceable().code == "ORDER_NOT_INVOICEABLE"
    assert customer_tax_id_required().code == "CUSTOMER_TAX_ID_REQUIRED"
    assert invoice_not_payable().code == "INVOICE_NOT_PAYABLE"
    assert amount_mismatch().code == "PAYMENT_AMOUNT_MISMATCH"


def test_totals_for_uses_the_shared_rounding() -> None:
    class Line:
        def __init__(self, unit_price: str, quantity: int) -> None:
            self.unit_price = Decimal(unit_price)
            self.quantity = quantity

    totals = totals_for(
        [Line("9.50", 5), Line("6.25", 10)],
        Decimal("10.00"),
    )

    assert totals.subtotal == Decimal("110.00")
    assert totals.tax == Decimal("11.00")
    assert totals.total == Decimal("121.00")
