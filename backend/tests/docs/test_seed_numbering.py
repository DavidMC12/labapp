"""The numbering notes after the seed, as docs/SEED.md states them."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal

from app.modules.customers.adapters.memory import InMemoryCustomerRepository
from app.modules.customers.seed import seed_customers
from app.modules.invoices.adapters.memory import InMemoryInvoiceStore
from app.modules.invoices.gateway import FakeGateway
from app.modules.invoices.models import PaymentAttempt, StoredResponse
from app.modules.invoices.seed import seed_invoices, seed_payments
from app.modules.orders.adapters.memory import InMemoryOrderStore
from app.modules.orders.seed import seed_orders, seed_products

from . import support

_NEXT_ORDER = re.compile(r"next order is `(?P<number>[A-Z]+-[0-9]+)`")
_NEXT_INVOICE = re.compile(r"next invoice `(?P<number>[A-Z]+-[0-9]+)`")
_NEXT_PAYMENT = re.compile(r"next payment id (?P<id>[0-9]+)")


def test_the_next_numbers_after_the_seed_match_the_document() -> None:
    text = support.seed_text()
    order_match = _NEXT_ORDER.search(text)
    invoice_match = _NEXT_INVOICE.search(text)
    payment_match = _NEXT_PAYMENT.search(text)
    assert order_match is not None
    assert invoice_match is not None
    assert payment_match is not None

    now = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)
    customers = InMemoryCustomerRepository(seed_customers())
    orders = InMemoryOrderStore(customers)
    orders.replace_all(seed_products(), seed_orders(), Decimal("10.00"))
    invoices = InMemoryInvoiceStore(orders, customers, FakeGateway())
    invoices.replace_all(seed_invoices(), seed_payments())

    created = orders.create_order(1, now)
    assert created.number == order_match.group("number")

    invoice = invoices.issue_invoice(2, None, now)
    assert invoice.number == invoice_match.group("number")

    invoices.register_payment(
        invoice.id,
        key="key-1",
        fingerprint="fp-1",
        expected_version=None,
        attempt=PaymentAttempt("cash", invoice.total, None, None),
        respond=lambda payment, after: StoredResponse(201, {}),
        now=now,
    )
    assert invoices.get_invoice(invoice.id).payments[-1].id == int(payment_match.group("id"))
