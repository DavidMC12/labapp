"""PostgreSQL invoice store.

Every method runs in one transaction. The lock order is: the order row
(``SELECT ... FOR UPDATE``) first, then the invoice row (``FOR NO KEY UPDATE``) and
then the customer row (``FOR SHARE``) when the snapshot needs it. A method that starts
from an invoice id reads ``invoices.order_id`` without a lock (it never changes), locks
the order, and only then locks the invoice and reads it again.

The invoice row is always locked with ``FOR NO KEY UPDATE``
(``with_for_update(key_share=True)``): a plain ``FOR UPDATE`` conflicts with the
``FOR KEY SHARE`` lock that the foreign key of a ``payments`` or ``idempotency_keys``
insert takes on the invoice, and two payments that claimed their keys before locking
would deadlock. ``PostgresOrderStore.transition`` uses the same mode when it voids an
invoice.

``register_payment`` claims the idempotency key before any lock: it deletes an expired
row of the same ``(invoice_id, key)`` and then inserts the placeholder row
(``status_code = 0``, ``response = '{}'``) with ``ON CONFLICT DO NOTHING``. The unique
row serializes two requests with the same key; the second either replays the committed
row or raises ``IDEMPOTENCY_KEY_REUSED``. A rejected request rolls the whole
transaction back, claim included, so it does not consume the key. ``respond`` is
rendered and stored in that row inside the same transaction, so every committed key
holds a final response.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import psycopg
from sqlalchemy import delete, func, insert, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError

from app.domain.money import MIN_TAX_RATE
from app.domain.numbering import format_number
from app.domain.orders import OrderStatus
from app.infra.db import (
    as_utc,
    qualified_sequence_name,
    qualified_table_name,
    unique_violation_of,
)
from app.modules.customers.search import normalize_for_search
from app.modules.customers.tables import customers
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
from app.modules.invoices.tables import (
    idempotency_keys,
    invoice_lines,
    invoice_number_seq,
    invoices,
    payments,
)
from app.modules.orders.adapters.postgres import attach_invoice_in, mark_paid_in
from app.modules.orders.ports import CustomerNotFound, OrderNotFound, VersionConflict
from app.modules.orders.tables import order_lines, orders

KEY_LIFETIME = timedelta(hours=24)

_INVOICE_ORDER_CONSTRAINT = "invoices_order_key"
_KEY_INVOICE_CONSTRAINT = "fk_idempotency_keys_invoice_id_invoices"

_STATUS_BY_OUTCOME = {
    "approved": PaymentStatus.APPROVED,
    "declined": PaymentStatus.DECLINED,
    "unavailable": PaymentStatus.FAILED,
}


@dataclass(frozen=True)
class _PricedLine:
    """The part of an order line that the totals need."""

    unit_price: Decimal
    quantity: int


def _number_value(number: str) -> int:
    return int(number.rsplit("-", 1)[-1])


def _foreign_key_violation_of(error: BaseException, constraint_name: str) -> bool:
    """Tell whether the error is a foreign key violation of exactly that constraint."""
    original = getattr(error, "orig", None)
    if not isinstance(original, psycopg.errors.ForeignKeyViolation):
        return False
    return original.diag.constraint_name == constraint_name


def _invoice_line_from_row(row: Mapping[str, Any]) -> InvoiceLine:
    return InvoiceLine(
        id=row["id"],
        product_id=row["product_id"],
        sku=row["sku"],
        name=row["name"],
        quantity=row["quantity"],
        unit_price=row["unit_price"],
    )


def _payment_from_row(row: Mapping[str, Any]) -> Payment:
    return Payment(
        id=row["id"],
        invoice_id=row["invoice_id"],
        method=row["method"],
        status=PaymentStatus(row["status"]),
        amount=row["amount"],
        reference=row["reference"],
        card_last4=row["card_last4"],
        reason=row["reason"],
        created_at=as_utc(row["created_at"]),
    )


def _invoice_from_row(
    row: Mapping[str, Any],
    lines: Iterable[InvoiceLine] = (),
    payments: Iterable[Payment] = (),
) -> Invoice:
    return Invoice(
        id=row["id"],
        number=row["number"],
        status=InvoiceStatus(row["status"]),
        order_id=row["order_id"],
        order_number=row["order_number"],
        customer_id=row["customer_id"],
        customer_name=row["customer_name"],
        customer_tax_id=row["customer_tax_id"],
        customer_address=row["customer_address"],
        lines=tuple(lines),
        subtotal=row["subtotal"],
        tax_rate=row["tax_rate"],
        tax=row["tax"],
        total=row["total"],
        version=row["version"],
        created_at=as_utc(row["created_at"]),
        updated_at=as_utc(row["updated_at"]),
        payments=tuple(payments),
    )


def _load_lines(connection: Connection, invoice_id: int) -> list[InvoiceLine]:
    rows = (
        connection.execute(
            select(invoice_lines)
            .where(invoice_lines.c.invoice_id == invoice_id)
            .order_by(invoice_lines.c.id)
        )
        .mappings()
        .all()
    )
    return [_invoice_line_from_row(row) for row in rows]


def _load_payments(connection: Connection, invoice_id: int) -> list[Payment]:
    rows = (
        connection.execute(
            select(payments).where(payments.c.invoice_id == invoice_id).order_by(payments.c.id)
        )
        .mappings()
        .all()
    )
    return [_payment_from_row(row) for row in rows]


def _load_invoice(connection: Connection, invoice_id: int) -> Invoice | None:
    row = connection.execute(select(invoices).where(invoices.c.id == invoice_id)).mappings().first()
    if row is None:
        return None
    return _invoice_from_row(
        row,
        _load_lines(connection, invoice_id),
        _load_payments(connection, invoice_id),
    )


def _lock_order(connection: Connection, order_id: int) -> Mapping[str, Any] | None:
    return (
        connection.execute(select(orders).where(orders.c.id == order_id).with_for_update())
        .mappings()
        .first()
    )


def _lock_invoice(connection: Connection, invoice_id: int) -> Mapping[str, Any] | None:
    return (
        connection.execute(
            select(invoices).where(invoices.c.id == invoice_id).with_for_update(key_share=True)
        )
        .mappings()
        .first()
    )


def _lock_customer(connection: Connection, customer_id: int) -> Mapping[str, Any] | None:
    return (
        connection.execute(
            select(
                customers.c.id,
                customers.c.name,
                customers.c.tax_id,
                customers.c.address,
            )
            .where(customers.c.id == customer_id)
            .with_for_update(read=True)
        )
        .mappings()
        .first()
    )


class PostgresInvoiceStore:
    """An invoice store backed by PostgreSQL."""

    def __init__(self, engine: Engine, gateway: PaymentGateway) -> None:
        self._engine = engine
        self._gateway = gateway

    def list_invoices(
        self,
        *,
        query: str | None,
        status: InvoiceStatus | None,
        order_id: int | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Invoice], int]:
        filters = []
        if status is not None:
            filters.append(invoices.c.status == status.value)
        if order_id is not None:
            filters.append(invoices.c.order_id == order_id)
        if query is not None:
            normalized = normalize_for_search(query)
            filters.append(
                or_(
                    func.lower(invoices.c.number).contains(normalized, autoescape=True),
                    invoices.c.customer_name_search.contains(normalized, autoescape=True),
                )
            )

        offset = (page - 1) * page_size
        with self._engine.begin() as connection:
            total = connection.execute(
                select(func.count()).select_from(invoices).where(*filters)
            ).scalar_one()
            rows = (
                connection.execute(
                    select(invoices)
                    .where(*filters)
                    .order_by(invoices.c.created_at.desc(), invoices.c.id.desc())
                    .offset(offset)
                    .limit(page_size)
                )
                .mappings()
                .all()
            )
        return [_invoice_from_row(row) for row in rows], total

    def get_invoice(self, id: int) -> Invoice | None:
        with self._engine.begin() as connection:
            return _load_invoice(connection, id)

    def find_key(self, invoice_id: int, key: str, now: datetime) -> StoredKey | None:
        cutoff = now - KEY_LIFETIME
        with self._engine.begin() as connection:
            row = (
                connection.execute(
                    select(
                        idempotency_keys.c.fingerprint,
                        idempotency_keys.c.status_code,
                        idempotency_keys.c.response,
                    ).where(
                        idempotency_keys.c.invoice_id == invoice_id,
                        idempotency_keys.c.key == key,
                        idempotency_keys.c.created_at > cutoff,
                    )
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        return StoredKey(
            fingerprint=row["fingerprint"],
            response=StoredResponse(row["status_code"], row["response"]),
        )

    def issue_invoice(
        self,
        order_id: int,
        expected_order_version: int | None,
        now: datetime,
    ) -> Invoice:
        try:
            with self._engine.begin() as connection:
                order = _lock_order(connection, order_id)
                if order is None:
                    raise OrderNotFound
                customer = _lock_customer(connection, order["customer_id"])
                if customer is None:
                    raise CustomerNotFound
                if (
                    expected_order_version is not None
                    and expected_order_version != order["version"]
                ):
                    raise VersionConflict
                rules.ensure_can_invoice(
                    OrderStatus(order["status"]),
                    order["invoice_id"] is not None,
                    customer["tax_id"],
                )

                line_rows = (
                    connection.execute(
                        select(order_lines)
                        .where(order_lines.c.order_id == order_id)
                        .order_by(order_lines.c.id)
                    )
                    .mappings()
                    .all()
                )
                rate = order["tax_rate"] if order["tax_rate"] is not None else MIN_TAX_RATE
                totals = rules.totals_for(
                    [_PricedLine(row["unit_price"], row["quantity"]) for row in line_rows],
                    rate,
                )
                number = connection.execute(
                    text("select nextval(CAST(:sequence_name AS regclass))"),
                    {"sequence_name": qualified_sequence_name(self._engine, invoice_number_seq)},
                ).scalar_one()
                invoice_row = (
                    connection.execute(
                        insert(invoices)
                        .values(
                            number=format_number("FAC", number),
                            status=InvoiceStatus.ISSUED.value,
                            order_id=order_id,
                            order_number=order["number"],
                            customer_id=customer["id"],
                            customer_name=customer["name"],
                            customer_name_search=normalize_for_search(customer["name"]),
                            customer_tax_id=customer["tax_id"] or "",
                            customer_address=customer["address"],
                            subtotal=totals.subtotal,
                            tax=totals.tax,
                            total=totals.total,
                            tax_rate=rate,
                            version=1,
                            created_at=now,
                            updated_at=now,
                        )
                        .returning(*invoices.c)
                    )
                    .mappings()
                    .one()
                )
                line_snapshot = [
                    _invoice_line_from_row(
                        connection.execute(
                            insert(invoice_lines)
                            .values(
                                invoice_id=invoice_row["id"],
                                product_id=row["product_id"],
                                sku=row["sku"],
                                name=row["name"],
                                quantity=row["quantity"],
                                unit_price=row["unit_price"],
                            )
                            .returning(*invoice_lines.c)
                        )
                        .mappings()
                        .one()
                    )
                    for row in line_rows
                ]
                attach_invoice_in(connection, order_id, invoice_row["id"], now)
                return _invoice_from_row(invoice_row, line_snapshot)
        except IntegrityError as error:
            if unique_violation_of(error, _INVOICE_ORDER_CONSTRAINT):
                raise rules.invoice_already_exists() from error
            raise

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
        try:
            with self._engine.begin() as connection:
                replay = self._claim_key(connection, invoice_id, key, fingerprint, now)
                if replay is not None:
                    return replay

                order_id = connection.execute(
                    select(invoices.c.order_id).where(invoices.c.id == invoice_id)
                ).scalar_one_or_none()
                if order_id is None:
                    raise InvoiceNotFound
                if _lock_order(connection, order_id) is None:
                    raise OrderNotFound
                row = _lock_invoice(connection, invoice_id)
                if row is None:
                    raise InvoiceNotFound
                invoice = _invoice_from_row(
                    row,
                    _load_lines(connection, invoice_id),
                    _load_payments(connection, invoice_id),
                )

                if expected_version is not None and expected_version != invoice.version:
                    raise VersionConflict
                rules.ensure_payable(invoice.status)
                rules.ensure_amount(attempt.amount, invoice.total)

                decision = self._gateway.charge(
                    attempt.method,
                    attempt.amount,
                    attempt.card_last4,
                )
                payment = _payment_from_row(
                    connection.execute(
                        insert(payments)
                        .values(
                            invoice_id=invoice_id,
                            method=attempt.method,
                            status=_STATUS_BY_OUTCOME[decision.outcome].value,
                            amount=attempt.amount,
                            reference=attempt.reference,
                            card_last4=attempt.card_last4,
                            reason=decision.reason,
                            created_at=now,
                        )
                        .returning(*payments.c)
                    )
                    .mappings()
                    .one()
                )
                if payment.status == PaymentStatus.APPROVED:
                    connection.execute(
                        update(invoices)
                        .where(invoices.c.id == invoice_id)
                        .values(
                            status=InvoiceStatus.PAID.value,
                            version=invoice.version + 1,
                            updated_at=now,
                        )
                    )
                    mark_paid_in(connection, order_id, now)

                invoice_after = _load_invoice(connection, invoice_id)
                assert invoice_after is not None
                response = respond(payment, invoice_after)
                connection.execute(
                    update(idempotency_keys)
                    .where(
                        idempotency_keys.c.invoice_id == invoice_id,
                        idempotency_keys.c.key == key,
                    )
                    .values(status_code=response.status_code, response=response.body)
                )
                return PaymentOutcome(response, False)
        except IntegrityError as error:
            if _foreign_key_violation_of(error, _KEY_INVOICE_CONSTRAINT):
                raise InvoiceNotFound from error
            raise

    def _claim_key(
        self,
        connection: Connection,
        invoice_id: int,
        key: str,
        fingerprint: str,
        now: datetime,
    ) -> PaymentOutcome | None:
        """Claim the key and return a replay, or ``None`` when the claim is ours."""
        cutoff = now - KEY_LIFETIME
        connection.execute(
            delete(idempotency_keys).where(
                idempotency_keys.c.invoice_id == invoice_id,
                idempotency_keys.c.key == key,
                idempotency_keys.c.created_at <= cutoff,
            )
        )
        claim = (
            postgres_insert(idempotency_keys)
            .values(
                invoice_id=invoice_id,
                key=key,
                fingerprint=fingerprint,
                status_code=0,
                response={},
                created_at=now,
            )
            .on_conflict_do_nothing(
                index_elements=[idempotency_keys.c.invoice_id, idempotency_keys.c.key]
            )
        )
        # RETURNING tells a claim that inserted from one that hit the conflict: with this driver
        # ``rowcount`` of the statement is -1, which is truthy.
        if connection.execute(claim.returning(idempotency_keys.c.key)).first() is not None:
            return None

        stored = (
            connection.execute(
                select(
                    idempotency_keys.c.fingerprint,
                    idempotency_keys.c.status_code,
                    idempotency_keys.c.response,
                ).where(
                    idempotency_keys.c.invoice_id == invoice_id,
                    idempotency_keys.c.key == key,
                )
            )
            .mappings()
            .one()
        )
        if stored["fingerprint"] != fingerprint:
            raise rules.key_reused()
        return PaymentOutcome(
            StoredResponse(stored["status_code"], stored["response"]),
            True,
        )

    def void_for_order(self, order_id: int, now: datetime) -> None:
        with self._engine.begin() as connection:
            if _lock_order(connection, order_id) is None:
                return
            row = (
                connection.execute(
                    select(invoices)
                    .where(invoices.c.order_id == order_id)
                    .with_for_update(key_share=True)
                )
                .mappings()
                .first()
            )
            if row is None or row["status"] != InvoiceStatus.ISSUED.value:
                return
            connection.execute(
                update(invoices)
                .where(invoices.c.id == row["id"])
                .values(
                    status=InvoiceStatus.VOID.value,
                    version=row["version"] + 1,
                    updated_at=now,
                )
            )

    def replace_all(
        self,
        invoice_rows: Iterable[Invoice],
        payment_rows: Iterable[Payment],
        *,
        connection: Connection | None = None,
    ) -> None:
        """Replace the invoices, payments and idempotency keys and link the orders.

        With ``connection`` it runs inside the caller's transaction and does not open
        its own; without it, the replacement is one transaction.
        """
        invoice_list = list(invoice_rows)
        payment_list = list(payment_rows)
        line_list = [(invoice.id, line) for invoice in invoice_list for line in invoice.lines]

        context = nullcontext(connection) if connection is not None else self._engine.begin()
        with context as connection:
            connection.execute(delete(payments))
            connection.execute(delete(idempotency_keys))
            connection.execute(delete(invoice_lines))
            connection.execute(delete(invoices))
            connection.execute(update(orders).values(invoice_id=None))

            if invoice_list:
                connection.execute(
                    insert(invoices).values(
                        [
                            {
                                "id": invoice.id,
                                "number": invoice.number,
                                "status": invoice.status.value,
                                "order_id": invoice.order_id,
                                "order_number": invoice.order_number,
                                "customer_id": invoice.customer_id,
                                "customer_name": invoice.customer_name,
                                "customer_name_search": normalize_for_search(invoice.customer_name),
                                "customer_tax_id": invoice.customer_tax_id,
                                "customer_address": invoice.customer_address,
                                "subtotal": invoice.subtotal,
                                "tax": invoice.tax,
                                "total": invoice.total,
                                "tax_rate": invoice.tax_rate,
                                "version": invoice.version,
                                "created_at": invoice.created_at,
                                "updated_at": invoice.updated_at,
                            }
                            for invoice in invoice_list
                        ]
                    )
                )
            if line_list:
                connection.execute(
                    insert(invoice_lines).values(
                        [
                            {
                                "id": line.id,
                                "invoice_id": invoice_id,
                                "product_id": line.product_id,
                                "sku": line.sku,
                                "name": line.name,
                                "quantity": line.quantity,
                                "unit_price": line.unit_price,
                            }
                            for invoice_id, line in line_list
                        ]
                    )
                )
            if payment_list:
                connection.execute(
                    insert(payments).values(
                        [
                            {
                                "id": payment.id,
                                "invoice_id": payment.invoice_id,
                                "method": payment.method,
                                "status": payment.status.value,
                                "amount": payment.amount,
                                "reference": payment.reference,
                                "card_last4": payment.card_last4,
                                "reason": payment.reason,
                                "created_at": payment.created_at,
                            }
                            for payment in payment_list
                        ]
                    )
                )

            for invoice in invoice_list:
                connection.execute(
                    update(orders)
                    .where(orders.c.id == invoice.order_id)
                    .values(invoice_id=invoice.id)
                )

            next_invoice_id = max((invoice.id for invoice in invoice_list), default=0) + 1
            next_line_id = max((line.id for _, line in line_list), default=0) + 1
            next_payment_id = max((payment.id for payment in payment_list), default=0) + 1
            next_number = (
                max((_number_value(invoice.number) for invoice in invoice_list), default=0) + 1
            )
            for table, next_value in (
                (invoices, next_invoice_id),
                (invoice_lines, next_line_id),
                (payments, next_payment_id),
            ):
                connection.execute(
                    text(
                        "select setval(CAST(pg_get_serial_sequence(:table_name, 'id') "
                        "AS regclass), :next_value, false)"
                    ),
                    {
                        "table_name": qualified_table_name(self._engine, table),
                        "next_value": next_value,
                    },
                )
            connection.execute(
                text("select setval(CAST(:sequence_name AS regclass), :next_value, false)"),
                {
                    "sequence_name": qualified_sequence_name(self._engine, invoice_number_seq),
                    "next_value": next_number,
                },
            )


__all__ = ["PostgresInvoiceStore"]
