"""Tests for the seeded invoices and payments."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.modules.customers.adapters.memory import InMemoryCustomerRepository
from app.modules.customers.seed import seed_customers
from app.modules.invoices.adapters.memory import InMemoryInvoiceStore
from app.modules.invoices.gateway import FakeGateway
from app.modules.invoices.models import (
    InvoiceStatus,
    PaymentAttempt,
    PaymentStatus,
    StoredResponse,
)
from app.modules.invoices.seed import seed_invoices, seed_payments
from app.modules.orders.adapters.memory import InMemoryOrderStore
from app.modules.orders.seed import seed_orders, seed_products


@pytest.fixture
def seeded_store():
    customers = InMemoryCustomerRepository(seed_customers())
    orders = InMemoryOrderStore(customers)
    orders.replace_all(seed_products(), seed_orders(), Decimal("10.00"))
    store = InMemoryInvoiceStore(orders, customers, FakeGateway())
    store.replace_all(seed_invoices(), seed_payments())
    orders.invoices = store
    return orders, store


def test_the_three_invoices_match_the_seed() -> None:
    invoices = seed_invoices()

    assert [invoice.number for invoice in invoices] == ["FAC-0001", "FAC-0002", "FAC-0003"]
    assert [invoice.order_id for invoice in invoices] == [3, 4, 5]
    assert [invoice.status for invoice in invoices] == [
        InvoiceStatus.ISSUED,
        InvoiceStatus.PAID,
        InvoiceStatus.PAID,
    ]
    assert [invoice.total for invoice in invoices] == [
        Decimal("327.80"),
        Decimal("197.97"),
        Decimal("768.90"),
    ]
    for invoice in invoices:
        assert invoice.version == 1
        assert invoice.updated_at == invoice.created_at


def test_the_four_payments_match_the_seed() -> None:
    payments = seed_payments()

    assert [payment.id for payment in payments] == [1, 2, 3, 4]
    assert [payment.status for payment in payments] == [
        PaymentStatus.DECLINED,
        PaymentStatus.FAILED,
        PaymentStatus.APPROVED,
        PaymentStatus.APPROVED,
    ]
    assert [payment.card_last4 for payment in payments] == ["0002", "0003", None, None]
    assert payments[2].reference == "TRF-2026-0001"
    assert [payment.reason for payment in payments] == [
        "CARD_DECLINED",
        "GATEWAY_UNAVAILABLE",
        None,
        None,
    ]


def test_every_seeded_payment_equals_its_invoice_total() -> None:
    invoices = {invoice.id: invoice for invoice in seed_invoices()}

    for payment in seed_payments():
        assert payment.amount == invoices[payment.invoice_id].total


def test_no_seeded_invoice_has_two_approved_payments() -> None:
    approved = [
        payment.invoice_id
        for payment in seed_payments()
        if payment.status == PaymentStatus.APPROVED
    ]

    assert len(approved) == len(set(approved))


def test_the_seed_links_the_orders_without_changing_them(seeded_store) -> None:
    orders, _ = seeded_store

    assert {order_id: orders.get_order(order_id).invoice_id for order_id in range(1, 8)} == {
        1: None,
        2: None,
        3: 1,
        4: 2,
        5: 3,
        6: None,
        7: None,
    }
    for order in (orders.get_order(3), orders.get_order(4), orders.get_order(5)):
        assert order.version == 1
        assert order.updated_at == order.created_at


def test_the_seed_continues_with_invoice_four_and_payment_five(seeded_store) -> None:
    _, store = seeded_store
    now = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)

    invoice = store.issue_invoice(2, None, now)
    assert invoice.number == "FAC-0004"
    store.register_payment(
        invoice.id,
        key="key-1",
        fingerprint="fp-1",
        expected_version=None,
        attempt=PaymentAttempt("cash", invoice.total, None, None),
        respond=lambda payment, after: StoredResponse(201, {}),
        now=now,
    )

    assert store.get_invoice(invoice.id).payments[-1].id == 5
