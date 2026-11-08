"""Concurrency behavior of the PostgreSQL invoice store."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from threading import Barrier

import pytest
from sqlalchemy import Engine, update

from app.domain.orders import OrderAction, OrderStatus
from app.errors import ApiError
from app.modules.customers.tables import customers
from app.modules.invoices.adapters.postgres import PostgresInvoiceStore
from app.modules.invoices.models import Invoice, Payment, StoredResponse
from app.modules.orders.adapters.postgres import PostgresOrderStore
from app.modules.orders.ports import VersionConflict
from tests.invoices.contract_store import attempt, respond

NOW = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)


def _pay(
    store: PostgresInvoiceStore,
    invoice_id: int,
    key: str,
    fingerprint: str,
    *,
    expected_version: int | None = None,
    amount: str = "327.80",
    card_last4: str = "4242",
    respond_with=respond,
):
    return store.register_payment(
        invoice_id,
        key=key,
        fingerprint=fingerprint,
        expected_version=expected_version,
        attempt=attempt(amount=amount, card_last4=card_last4),
        respond=respond_with,
        now=NOW,
    )


def _declined_response(payment: Payment, invoice: Invoice) -> StoredResponse:
    return StoredResponse(
        402,
        {"payment_id": payment.id, "reason": payment.reason, "invoice_id": invoice.id},
    )


def test_two_different_keys_approve_once_without_deadlock(
    postgres_invoice_store: PostgresInvoiceStore,
) -> None:
    barrier = Barrier(2)

    def pay(key: str) -> str:
        barrier.wait()
        try:
            _pay(postgres_invoice_store, 1, key, key)
        except ApiError as error:
            return error.code
        return "approved"

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(pay, key) for key in ("key-1", "key-2")]
        outcomes = [future.result(timeout=15) for future in futures]

    assert sorted(outcomes) == ["INVOICE_NOT_PAYABLE", "approved"]
    assert len(postgres_invoice_store.get_invoice(1).payments) == 3


def test_a_declined_key_replays_its_402_response(
    postgres_invoice_store: PostgresInvoiceStore,
) -> None:
    first = _pay(
        postgres_invoice_store,
        1,
        "key-1",
        "fp-1",
        card_last4="0002",
        respond_with=_declined_response,
    )
    second = _pay(
        postgres_invoice_store,
        1,
        "key-1",
        "fp-1",
        card_last4="0002",
        respond_with=_declined_response,
    )

    assert first.replayed is False
    assert first.response.status_code == 402
    assert second.replayed is True
    assert second.response == first.response
    assert postgres_invoice_store.get_invoice(1).status.value == "issued"
    assert len(postgres_invoice_store.get_invoice(1).payments) == 3


def test_a_rejected_payment_does_not_consume_the_key(
    postgres_invoice_store: PostgresInvoiceStore,
) -> None:
    with pytest.raises(ApiError) as mismatch:
        _pay(postgres_invoice_store, 1, "key-1", "fp-1", amount="1.00")
    assert mismatch.value.code == "PAYMENT_AMOUNT_MISMATCH"
    assert postgres_invoice_store.find_key(1, "key-1", NOW) is None

    with pytest.raises(VersionConflict):
        _pay(postgres_invoice_store, 1, "key-1", "fp-1", expected_version=99)
    assert postgres_invoice_store.find_key(1, "key-1", NOW) is None

    outcome = _pay(postgres_invoice_store, 1, "key-1", "fp-1")
    assert outcome.replayed is False
    assert outcome.response.body["payment_status"] == "approved"


def test_two_concurrent_issues_of_one_order_have_one_winner(
    postgres_invoice_store: PostgresInvoiceStore,
) -> None:
    barrier = Barrier(2)

    def issue() -> str:
        barrier.wait()
        try:
            postgres_invoice_store.issue_invoice(2, None, NOW)
        except ApiError as error:
            return error.code
        return "issued"

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(issue) for _ in range(2)]
        outcomes = [future.result(timeout=15) for future in futures]

    assert sorted(outcomes) == ["INVOICE_ALREADY_EXISTS", "issued"]
    invoices, total = postgres_invoice_store.list_invoices(
        query=None, status=None, order_id=2, page=1, page_size=20
    )
    assert total == 1
    assert len(invoices) == 1


def test_pay_and_cancel_race_ends_in_a_consistent_state(
    postgres_invoice_store: PostgresInvoiceStore,
    postgres_order_store: PostgresOrderStore,
) -> None:
    barrier = Barrier(2)

    def pay() -> str:
        barrier.wait()
        try:
            _pay(postgres_invoice_store, 1, "key-race", "fp-race")
        except ApiError as error:
            return error.code
        return "approved"

    def cancel() -> str:
        barrier.wait()
        try:
            postgres_order_store.transition(3, OrderAction.CANCEL, None, NOW)
        except ApiError as error:
            return error.code
        return "cancelled"

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(pay), executor.submit(cancel)]
        outcomes = [future.result(timeout=15) for future in futures]

    assert sorted(outcomes) in (
        ["INVALID_TRANSITION", "approved"],
        ["INVOICE_NOT_PAYABLE", "cancelled"],
    )
    order = postgres_order_store.get_order(3)
    invoice = postgres_invoice_store.get_invoice(1)
    if order.status == OrderStatus.PAID:
        assert invoice.status.value == "paid"
        assert invoice.version == 2
    else:
        assert order.status == OrderStatus.CANCELLED
        assert invoice.status.value == "void"
        assert postgres_invoice_store.find_key(1, "key-race", NOW) is None


def test_issue_waits_for_the_committed_customer_snapshot(
    postgres_invoice_store: PostgresInvoiceStore,
    postgres_order_store: PostgresOrderStore,
    unpinned_database_engine: Engine,
) -> None:
    with unpinned_database_engine.connect() as blocker:
        blocker.execute(
            update(customers)
            .where(customers.c.id == 2)
            .values(name="Beta Renombrada", tax_id="BETA-NEW", version=2)
        )
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(postgres_invoice_store.issue_invoice, 2, None, NOW)
            time.sleep(0.3)
            blocker.commit()
            invoice = future.result(timeout=15)

    assert invoice.customer_name == "Beta Renombrada"
    assert invoice.customer_tax_id == "BETA-NEW"
    assert postgres_order_store.get_order(2).invoice_id == invoice.id


def test_twenty_concurrent_issues_never_repeat_a_number(
    postgres_invoice_store: PostgresInvoiceStore,
    postgres_order_store: PostgresOrderStore,
) -> None:
    orders = []
    for _ in range(20):
        order = postgres_order_store.create_order(1, NOW)
        postgres_order_store.add_line(order.id, 14, 1, None, NOW)
        postgres_order_store.transition(order.id, OrderAction.CONFIRM, None, NOW)
        orders.append(order)
    barrier = Barrier(20)

    def issue(order_id: int) -> str:
        barrier.wait()
        return postgres_invoice_store.issue_invoice(order_id, None, NOW).number

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(issue, order.id) for order in orders]
        numbers = [future.result(timeout=30) for future in futures]

    assert len(set(numbers)) == 20
    assert {int(number.rsplit("-", 1)[-1]) for number in numbers} == set(range(4, 24))
    invoices = [postgres_invoice_store.get_invoice(invoice_id) for invoice_id in range(4, 24)]
    assert all(invoice.total == Decimal("16.49") for invoice in invoices)
    assert all(invoice.payments == () for invoice in invoices)
