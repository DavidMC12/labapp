"""Reusable behavioral tests for InvoiceStore adapters."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Barrier

import pytest

from app.domain.orders import OrderStatus
from app.errors import ApiError
from app.modules.customers.ports import CustomerRepository
from app.modules.invoices.gateway import FakeGateway
from app.modules.invoices.models import (
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    Payment,
    PaymentAttempt,
    PaymentStatus,
    StoredResponse,
)
from app.modules.invoices.ports import InvoiceNotFound
from app.modules.orders.ports import OrderNotFound, VersionConflict

NOW = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)
LATER = NOW + timedelta(minutes=1)


class CountingGateway:
    """A fake gateway that counts how many charges it answered."""

    def __init__(self) -> None:
        self.calls = 0
        self._fake = FakeGateway()

    def charge(self, method: str, amount: Decimal, card_last4: str | None):
        self.calls += 1
        return self._fake.charge(method, amount, card_last4)


def attempt(
    *,
    method: str = "card",
    amount: str = "327.80",
    card_last4: str | None = "4242",
    reference: str | None = None,
) -> PaymentAttempt:
    """Build a validated payment attempt."""
    return PaymentAttempt(
        method=method,
        amount=Decimal(amount),
        card_last4=card_last4,
        reference=reference,
    )


def respond(payment: Payment, invoice: Invoice) -> StoredResponse:
    """A minimal response function that records the invoice after the payment."""
    return StoredResponse(
        201,
        {
            "payment_id": payment.id,
            "payment_status": payment.status.value,
            "invoice_status": invoice.status.value,
            "invoice_version": invoice.version,
            "payments": len(invoice.payments),
        },
    )


def _pay(store, invoice_id: int, key: str, fingerprint: str, *, expected_version=None, **kwargs):
    return store.register_payment(
        invoice_id,
        key=key,
        fingerprint=fingerprint,
        expected_version=expected_version,
        attempt=attempt(**kwargs),
        respond=respond,
        now=NOW,
    )


class InvoiceStoreContract:
    """The behavior every InvoiceStore adapter must share.

    A concrete class provides ``customer_repository``, ``order_store`` (seeded
    with the products and orders) and ``store`` (seeded with the invoices and
    payments).
    """

    @pytest.fixture
    def customer_repository(self) -> CustomerRepository:
        raise NotImplementedError

    @pytest.fixture
    def gateway(self) -> CountingGateway:
        return CountingGateway()

    @pytest.fixture
    def order_store(self, customer_repository: CustomerRepository):
        raise NotImplementedError

    @pytest.fixture
    def store(self, order_store, customer_repository: CustomerRepository, gateway: CountingGateway):
        raise NotImplementedError

    def test_seed_invoices_are_loaded(self, store) -> None:
        invoices, total = store.list_invoices(
            query=None, status=None, order_id=None, page=1, page_size=20
        )

        assert total == 3
        assert [invoice.id for invoice in invoices] == [3, 2, 1]
        assert all(invoice.lines == () and invoice.payments == () for invoice in invoices)

    def test_get_invoice_returns_the_snapshot_and_payments(self, store) -> None:
        invoice = store.get_invoice(1)

        assert invoice is not None
        assert invoice.number == "FAC-0001"
        assert invoice.status == InvoiceStatus.ISSUED
        assert invoice.order_id == 3
        assert invoice.order_number == "PED-0003"
        assert invoice.customer_id == 4
        assert invoice.customer_name == "Distribuidora Delta"
        assert invoice.customer_tax_id == "DELT-700789"
        assert invoice.customer_address is None
        assert [(line.id, line.sku, line.quantity) for line in invoice.lines] == [(1, "MN-240", 2)]
        assert invoice.subtotal == Decimal("298.00")
        assert invoice.tax_rate == Decimal("10.00")
        assert invoice.tax == Decimal("29.80")
        assert invoice.total == Decimal("327.80")
        assert invoice.version == 1
        assert invoice.updated_at == invoice.created_at
        assert [payment.id for payment in invoice.payments] == [1, 2]
        assert store.get_invoice(99) is None

    def test_list_filters_by_status_and_order(self, store) -> None:
        issued, _ = store.list_invoices(
            query=None, status=InvoiceStatus.ISSUED, order_id=None, page=1, page_size=20
        )
        paid, _ = store.list_invoices(
            query=None, status=InvoiceStatus.PAID, order_id=None, page=1, page_size=20
        )
        by_order, _ = store.list_invoices(query=None, status=None, order_id=4, page=1, page_size=20)

        assert [invoice.id for invoice in issued] == [1]
        assert [invoice.id for invoice in paid] == [3, 2]
        assert [invoice.id for invoice in by_order] == [2]

    def test_list_searches_number_and_snapshot_name(self, store) -> None:
        by_number, _ = store.list_invoices(
            query="fac-0002", status=None, order_id=None, page=1, page_size=20
        )
        by_name, _ = store.list_invoices(
            query="iberica", status=None, order_id=None, page=1, page_size=20
        )
        by_accent, _ = store.list_invoices(
            query="IBÉRICA", status=None, order_id=None, page=1, page_size=20
        )

        assert [invoice.id for invoice in by_number] == [2]
        assert [invoice.id for invoice in by_name] == [3]
        assert [invoice.id for invoice in by_accent] == [3]

    def test_list_pages(self, store) -> None:
        first, total = store.list_invoices(
            query=None, status=None, order_id=None, page=1, page_size=2
        )
        second, _ = store.list_invoices(query=None, status=None, order_id=None, page=2, page_size=2)
        empty, _ = store.list_invoices(query=None, status=None, order_id=None, page=3, page_size=2)

        assert total == 3
        assert [invoice.id for invoice in first] == [3, 2]
        assert [invoice.id for invoice in second] == [1]
        assert empty == []

    def test_issue_copies_the_snapshot_and_bumps_the_order(self, store, order_store) -> None:
        invoice = store.issue_invoice(2, 1, NOW)

        assert invoice.id == 4
        assert invoice.number == "FAC-0004"
        assert invoice.status == InvoiceStatus.ISSUED
        assert invoice.order_id == 2
        assert invoice.order_number == "PED-0002"
        assert invoice.customer_id == 2
        assert invoice.customer_name == "Beta Comercial Ltda."
        assert invoice.customer_tax_id == "BETA-800456"
        assert invoice.lines[0].id == 4
        assert invoice.lines[1].id == 5
        assert invoice.subtotal == Decimal("110.00")
        assert invoice.tax == Decimal("11.00")
        assert invoice.total == Decimal("121.00")
        assert invoice.version == 1
        assert invoice.created_at == NOW
        assert invoice.updated_at == NOW
        order = order_store.get_order(2)
        assert order.invoice_id == 4
        assert order.version == 2
        assert order.updated_at == NOW

    def test_issue_checks_in_the_documented_order(self, store) -> None:
        with pytest.raises(OrderNotFound):
            store.issue_invoice(99, None, NOW)
        with pytest.raises(VersionConflict):
            store.issue_invoice(3, 99, NOW)
        with pytest.raises(ApiError) as exists:
            store.issue_invoice(3, 1, NOW)
        assert exists.value.code == "INVOICE_ALREADY_EXISTS"
        with pytest.raises(ApiError) as not_invoiceable:
            store.issue_invoice(1, None, NOW)
        assert not_invoiceable.value.code == "ORDER_NOT_INVOICEABLE"
        with pytest.raises(ApiError) as tax_id:
            store.issue_invoice(7, None, NOW)
        assert tax_id.value.code == "CUSTOMER_TAX_ID_REQUIRED"

    def test_the_snapshot_does_not_change_with_the_customer(
        self, store, customer_repository: CustomerRepository
    ) -> None:
        invoice = store.issue_invoice(2, 1, NOW)
        customer_repository.update(2, {"name": "Renamed", "tax_id": "NEW-1"}, None, LATER)

        reread = store.get_invoice(invoice.id)

        assert reread.customer_name == "Beta Comercial Ltda."
        assert reread.customer_tax_id == "BETA-800456"

    def test_an_approved_payment_pays_the_invoice_and_the_order(self, store, order_store, gateway):
        outcome = _pay(store, 1, "key-1", "fp-1")

        assert outcome.replayed is False
        assert outcome.response.status_code == 201
        assert outcome.response.body["payment_id"] == 5
        assert outcome.response.body["payment_status"] == "approved"
        assert outcome.response.body["invoice_status"] == "paid"
        assert outcome.response.body["invoice_version"] == 2
        assert outcome.response.body["payments"] == 3
        assert gateway.calls == 1
        invoice = store.get_invoice(1)
        assert invoice.status == InvoiceStatus.PAID
        assert invoice.version == 2
        assert invoice.updated_at == NOW
        assert [payment.id for payment in invoice.payments] == [1, 2, 5]
        assert invoice.payments[-1].card_last4 == "4242"
        assert invoice.payments[-1].reference is None
        order = order_store.get_order(3)
        assert order.status == OrderStatus.PAID
        assert order.version == 2

    @pytest.mark.parametrize(
        ("last4", "status", "reason"),
        [
            ("0002", PaymentStatus.DECLINED, "CARD_DECLINED"),
            ("0003", PaymentStatus.FAILED, "GATEWAY_UNAVAILABLE"),
        ],
    )
    def test_declined_and_failed_attempts_are_stored(
        self, store, order_store, last4, status, reason
    ) -> None:
        outcome = _pay(store, 1, "key-1", "fp-1", card_last4=last4)

        assert outcome.replayed is False
        assert outcome.response.status_code == 201
        invoice = store.get_invoice(1)
        assert invoice.status == InvoiceStatus.ISSUED
        assert invoice.version == 1
        assert invoice.payments[-1].id == 5
        assert invoice.payments[-1].status == status
        assert invoice.payments[-1].reason == reason
        order = order_store.get_order(3)
        assert order.status == OrderStatus.CONFIRMED
        assert order.version == 1

    @pytest.mark.parametrize(
        ("method", "last4", "reference"),
        [
            ("transfer", None, "TRF-2026-0001"),
            ("cash", None, None),
        ],
    )
    def test_transfer_and_cash_are_approved(self, store, method, last4, reference) -> None:
        _pay(
            store,
            1,
            "key-1",
            "fp-1",
            method=method,
            card_last4=last4,
            reference=reference,
        )

        payment = store.get_invoice(1).payments[-1]
        assert payment.status == PaymentStatus.APPROVED
        assert payment.reference == reference
        assert payment.card_last4 == last4

    def test_amount_mismatch_does_not_consume_the_key(self, store, gateway) -> None:
        with pytest.raises(ApiError) as error:
            _pay(store, 1, "key-1", "fp-1", amount="327.81")

        assert error.value.code == "PAYMENT_AMOUNT_MISMATCH"
        assert gateway.calls == 0
        assert store.find_key(1, "key-1", NOW) is None
        assert len(store.get_invoice(1).payments) == 2

    def test_a_paid_invoice_is_not_payable(self, store) -> None:
        with pytest.raises(ApiError) as error:
            _pay(store, 2, "key-1", "fp-1", amount="197.97")

        assert error.value.code == "INVOICE_NOT_PAYABLE"

    def test_the_stale_version_is_checked_first(self, store) -> None:
        with pytest.raises(VersionConflict):
            _pay(store, 2, "key-1", "fp-1", expected_version=9, amount="197.97")

    def test_an_unknown_invoice_is_not_found(self, store) -> None:
        with pytest.raises(InvoiceNotFound):
            _pay(store, 99, "key-1", "fp-1")

    def test_the_same_key_and_body_replays_the_stored_response(self, store, gateway) -> None:
        first = _pay(store, 1, "key-1", "fp-1")
        second = _pay(store, 1, "key-1", "fp-1")

        assert first.response == second.response
        assert first.replayed is False
        assert second.replayed is True
        assert gateway.calls == 1
        assert len(store.get_invoice(1).payments) == 3

    def test_the_same_key_with_another_body_is_reused(self, store) -> None:
        _pay(store, 1, "key-1", "fp-1")

        with pytest.raises(ApiError) as error:
            _pay(store, 1, "key-1", "fp-2")

        assert error.value.code == "IDEMPOTENCY_KEY_REUSED"

    def test_find_key_ignores_missing_and_expired_keys(self, store) -> None:
        _pay(store, 1, "key-1", "fp-1")

        assert store.find_key(1, "key-1", NOW + timedelta(hours=23)) is not None
        assert store.find_key(1, "key-1", NOW + timedelta(hours=24)) is None
        assert store.find_key(2, "key-1", NOW) is None

    def test_an_expired_key_can_be_used_again(self, store) -> None:
        _pay(store, 1, "key-1", "fp-1", card_last4="0002")

        outcome = store.register_payment(
            1,
            key="key-1",
            fingerprint="fp-1",
            expected_version=None,
            attempt=attempt(),
            respond=respond,
            now=NOW + timedelta(hours=24),
        )

        assert outcome.replayed is False
        assert outcome.response.body["payment_id"] == 6

    def test_void_for_order_voids_only_an_issued_invoice(self, store) -> None:
        store.void_for_order(3, LATER)

        invoice = store.get_invoice(1)
        assert invoice.status == InvoiceStatus.VOID
        assert invoice.version == 2
        assert invoice.updated_at == LATER

        store.void_for_order(3, LATER)
        assert store.get_invoice(1).version == 2
        store.void_for_order(4, LATER)
        assert store.get_invoice(2).status == InvoiceStatus.PAID

    def test_replace_all_restarts_the_counters_and_the_links(self, store, order_store) -> None:
        invoice = Invoice(
            id=7,
            number="FAC-0007",
            status=InvoiceStatus.ISSUED,
            order_id=1,
            order_number="PED-0001",
            customer_id=1,
            customer_name="Acme Industrial S.A.",
            customer_tax_id="ACME-900123",
            customer_address="Av. Principal 100",
            lines=(
                InvoiceLine(
                    id=10,
                    product_id=1,
                    sku="KB-100",
                    name="Teclado USB",
                    quantity=2,
                    unit_price=Decimal("19.90"),
                ),
            ),
            subtotal=Decimal("39.80"),
            tax_rate=Decimal("10.00"),
            tax=Decimal("3.98"),
            total=Decimal("43.78"),
            version=1,
            created_at=NOW,
            updated_at=NOW,
        )
        payment = Payment(
            id=9,
            invoice_id=7,
            method="cash",
            status=PaymentStatus.APPROVED,
            amount=Decimal("43.78"),
            reference=None,
            card_last4=None,
            reason=None,
            created_at=NOW,
        )

        store.replace_all([invoice], [payment])

        assert store.list_invoices(
            query=None, status=None, order_id=None, page=1, page_size=20
        ) == (
            [
                Invoice(
                    id=7,
                    number="FAC-0007",
                    status=InvoiceStatus.ISSUED,
                    order_id=1,
                    order_number="PED-0001",
                    customer_id=1,
                    customer_name="Acme Industrial S.A.",
                    customer_tax_id="ACME-900123",
                    customer_address="Av. Principal 100",
                    lines=(),
                    subtotal=Decimal("39.80"),
                    tax_rate=Decimal("10.00"),
                    tax=Decimal("3.98"),
                    total=Decimal("43.78"),
                    version=1,
                    created_at=NOW,
                    updated_at=NOW,
                )
            ],
            1,
        )
        assert order_store.get_order(1).invoice_id == 7
        assert order_store.get_order(3).invoice_id is None
        created = store.issue_invoice(2, None, LATER)
        assert created.id == 8
        assert created.number == "FAC-0008"
        assert created.lines[0].id == 11

    def test_replace_all_clears_the_keys(self, store) -> None:
        _pay(store, 1, "key-1", "fp-1")

        store.replace_all([], [])

        assert store.find_key(1, "key-1", NOW) is None

    def test_two_concurrent_payments_with_the_same_key_make_one_payment(
        self, store, gateway
    ) -> None:
        barrier = Barrier(2)

        def pay() -> bool:
            barrier.wait()
            return _pay(store, 1, "key-1", "fp-1").replayed

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(pay) for _ in range(2)]
            outcomes = [future.result(timeout=10) for future in futures]

        assert sorted(outcomes) == [False, True]
        assert gateway.calls == 1
        assert len(store.get_invoice(1).payments) == 3

    def test_two_concurrent_payments_with_different_keys_approve_once(self, store, gateway) -> None:
        barrier = Barrier(2)

        def pay(key: str) -> str:
            barrier.wait()
            try:
                _pay(store, 1, key, key)
            except ApiError as error:
                return error.code
            return "approved"

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(pay, key) for key in ("key-1", "key-2")]
            outcomes = [future.result(timeout=10) for future in futures]

        assert sorted(outcomes) == ["INVOICE_NOT_PAYABLE", "approved"]
        assert gateway.calls == 1
        assert len(store.get_invoice(1).payments) == 3
