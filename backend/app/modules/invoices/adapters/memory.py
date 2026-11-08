"""In-memory invoice store (a test double and development aid)."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from threading import RLock

from app.domain.numbering import format_number
from app.domain.sorting import SortSpec
from app.modules.customers.ports import CustomerNotFound, CustomerRepository
from app.modules.customers.search import normalize_for_search
from app.modules.invoices import rules
from app.modules.invoices.gateway import PaymentGateway
from app.modules.invoices.models import (
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    Payment,
    PaymentAttempt,
    PaymentOutcome,
    PaymentStatus,
    StoredKey,
    StoredResponse,
)
from app.modules.invoices.ports import InvoiceNotFound
from app.modules.orders.ports import OrderNotFound, OrderStore, VersionConflict

KEY_LIFETIME = timedelta(hours=24)

_STATUS_BY_OUTCOME = {
    "approved": PaymentStatus.APPROVED,
    "declined": PaymentStatus.DECLINED,
    "unavailable": PaymentStatus.FAILED,
}


_DEFAULT_SORT = SortSpec("created_at", True)


def _number_value(number: str) -> int:
    return int(number.rsplit("-", 1)[-1])


def _invoice_sort_key(invoice: Invoice, field: str):
    if field == "number":
        return _number_value(invoice.number), invoice.id
    if field == "customer":
        return normalize_for_search(invoice.customer_name), invoice.id
    if field == "total":
        return invoice.total, invoice.id
    return invoice.created_at, invoice.id


class InMemoryInvoiceStore:
    """A thread-safe invoice store backed by dictionaries.

    The lock is normally the same ``RLock`` as the order store's, because the
    two stores call each other while holding it.
    """

    def __init__(
        self,
        orders: OrderStore,
        customers: CustomerRepository,
        gateway: PaymentGateway,
        lock: RLock | None = None,
    ) -> None:
        self._orders = orders
        self._customers = customers
        self._gateway = gateway
        self._lock = lock if lock is not None else RLock()
        self._invoices: dict[int, Invoice] = {}
        self._payments: dict[int, Payment] = {}
        self._keys: dict[tuple[int, str], tuple[str, StoredResponse, datetime]] = {}
        self._next_invoice_id = 1
        self._next_line_id = 1
        self._next_number = 1
        self._next_payment_id = 1

    def list_invoices(
        self,
        *,
        query: str | None,
        status: InvoiceStatus | None,
        order_id: int | None,
        page: int,
        page_size: int,
        sort: SortSpec | None = None,
    ) -> tuple[list[Invoice], int]:
        spec = sort or _DEFAULT_SORT
        with self._lock:
            matches: list[Invoice] = []
            for invoice in self._invoices.values():
                if status is not None and invoice.status != status:
                    continue
                if order_id is not None and invoice.order_id != order_id:
                    continue
                if query is not None:
                    needle = normalize_for_search(query)
                    if needle not in normalize_for_search(
                        invoice.number
                    ) and needle not in normalize_for_search(invoice.customer_name):
                        continue
                matches.append(invoice)
            matches.sort(
                key=lambda invoice: _invoice_sort_key(invoice, spec.field),
                reverse=spec.descending,
            )
            start = (page - 1) * page_size
            return [
                replace(invoice, lines=(), payments=())
                for invoice in matches[start : start + page_size]
            ], len(matches)

    def get_invoice(self, id: int) -> Invoice | None:
        with self._lock:
            invoice = self._invoices.get(id)
            if invoice is None:
                return None
            return self._with_payments(invoice)

    def find_key(self, invoice_id: int, key: str, now: datetime) -> StoredKey | None:
        with self._lock:
            stored = self._keys.get((invoice_id, key))
            if stored is None:
                return None
            fingerprint, response, created_at = stored
            if now - created_at >= KEY_LIFETIME:
                return None
            return StoredKey(fingerprint=fingerprint, response=response)

    def issue_invoice(
        self,
        order_id: int,
        expected_order_version: int | None,
        now: datetime,
    ) -> Invoice:
        with self._lock:
            order = self._orders.get_order(order_id)
            if order is None:
                raise OrderNotFound
            customer = self._customers.get(order.customer_id)
            if customer is None:
                raise CustomerNotFound
            if expected_order_version is not None and expected_order_version != order.version:
                raise VersionConflict
            rules.ensure_can_invoice(
                order.status,
                order.invoice_id is not None,
                customer.tax_id,
            )
            lines = tuple(
                InvoiceLine(
                    id=self._next_line_id + position,
                    product_id=line.product_id,
                    sku=line.sku,
                    name=line.name,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                )
                for position, line in enumerate(order.lines)
            )
            rate = order.tax_rate if order.tax_rate is not None else Decimal("0.00")
            totals = rules.totals_for(lines, rate)
            invoice = Invoice(
                id=self._next_invoice_id,
                number=format_number("FAC", self._next_number),
                status=InvoiceStatus.ISSUED,
                order_id=order.id,
                order_number=order.number,
                customer_id=customer.id,
                customer_name=customer.name,
                customer_tax_id=customer.tax_id or "",
                customer_address=customer.address,
                lines=lines,
                subtotal=totals.subtotal,
                tax_rate=rate,
                tax=totals.tax,
                total=totals.total,
                version=1,
                created_at=now,
                updated_at=now,
            )
            self._next_invoice_id += 1
            self._next_number += 1
            self._next_line_id += len(lines)
            self._invoices[invoice.id] = invoice
            self._orders.attach_invoice(order.id, invoice.id, now)
            return invoice

    def register_payment(
        self,
        invoice_id: int,
        *,
        key: str,
        fingerprint: str,
        expected_version: int | None,
        attempt: PaymentAttempt,
        respond: Callable[[Payment, Invoice], StoredResponse],
        now: datetime,
    ) -> PaymentOutcome:
        with self._lock:
            expired = [
                stored_key
                for stored_key, (_, _, created_at) in self._keys.items()
                if stored_key[0] == invoice_id and now - created_at >= KEY_LIFETIME
            ]
            for stored_key in expired:
                del self._keys[stored_key]

            stored = self._keys.get((invoice_id, key))
            if stored is not None:
                stored_fingerprint, stored_response, _ = stored
                if stored_fingerprint == fingerprint:
                    return PaymentOutcome(stored_response, True)
                raise rules.key_reused()

            invoice = self._invoices.get(invoice_id)
            if invoice is None:
                raise InvoiceNotFound
            order = self._orders.get_order(invoice.order_id)
            if order is None:
                raise OrderNotFound
            if expected_version is not None and expected_version != invoice.version:
                raise VersionConflict
            rules.ensure_payable(invoice.status)
            rules.ensure_amount(attempt.amount, invoice.total)

            # A real gateway that raised or timed out would need its own handling:
            # record a failed payment outside this transaction. Today only the fake
            # gateway exists and the fault gateway raises nothing.
            decision = self._gateway.charge(attempt.method, attempt.amount, attempt.card_last4)
            payment = Payment(
                id=self._next_payment_id,
                invoice_id=invoice_id,
                method=attempt.method,
                status=_STATUS_BY_OUTCOME[decision.outcome],
                amount=attempt.amount,
                reference=attempt.reference,
                card_last4=attempt.card_last4,
                reason=decision.reason,
                created_at=now,
            )

            updated_invoice = invoice
            if payment.status == PaymentStatus.APPROVED:
                self._orders.mark_paid(order.id, now)
                updated_invoice = replace(
                    invoice,
                    status=InvoiceStatus.PAID,
                    version=invoice.version + 1,
                    updated_at=now,
                )

            self._next_payment_id += 1
            self._payments[payment.id] = payment
            self._invoices[invoice.id] = updated_invoice
            invoice_after = self._with_payments(self._invoices[invoice.id])
            response = respond(payment, invoice_after)
            self._keys[(invoice_id, key)] = (fingerprint, response, now)
            return PaymentOutcome(response, False)

    def void_for_order(self, order_id: int, now: datetime) -> None:
        with self._lock:
            for invoice in self._invoices.values():
                if invoice.order_id == order_id and invoice.status == InvoiceStatus.ISSUED:
                    self._invoices[invoice.id] = replace(
                        invoice,
                        status=InvoiceStatus.VOID,
                        version=invoice.version + 1,
                        updated_at=now,
                    )
                    return

    def replace_all(
        self,
        invoices: Iterable[Invoice],
        payments: Iterable[Payment],
    ) -> None:
        invoice_list = list(invoices)
        payment_list = list(payments)
        with self._lock:
            self._invoices = {invoice.id: replace(invoice, payments=()) for invoice in invoice_list}
            self._payments = {payment.id: payment for payment in payment_list}
            self._keys = {}
            self._next_invoice_id = max((invoice.id for invoice in invoice_list), default=0) + 1
            self._next_line_id = (
                max(
                    (line.id for invoice in invoice_list for line in invoice.lines),
                    default=0,
                )
                + 1
            )
            self._next_number = (
                max((_number_value(invoice.number) for invoice in invoice_list), default=0) + 1
            )
            self._next_payment_id = max((payment.id for payment in payment_list), default=0) + 1
            self._orders.link_invoices({invoice.order_id: invoice.id for invoice in invoice_list})

    def _with_payments(self, invoice: Invoice) -> Invoice:
        payments = tuple(
            sorted(
                (
                    payment
                    for payment in self._payments.values()
                    if payment.invoice_id == invoice.id
                ),
                key=lambda payment: payment.id,
            )
        )
        return replace(invoice, payments=payments)
