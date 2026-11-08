"""The invoice tables reject what their constraints and indexes should reject."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import Connection, func, insert, select
from sqlalchemy.exc import IntegrityError

from app.modules.invoices.adapters.postgres import PostgresInvoiceStore
from app.modules.invoices.tables import invoices, payments

NOW = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)


def _invoice_values(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "number": "FAC-9999",
        "status": "issued",
        "order_id": 2,
        "order_number": "PED-0002",
        "customer_id": 2,
        "customer_name": "Beta Comercial Ltda.",
        "customer_name_search": "beta comercial ltda.",
        "customer_tax_id": "BETA-800456",
        "customer_address": None,
        "subtotal": Decimal("1.00"),
        "tax": Decimal("0.10"),
        "total": Decimal("1.10"),
        "tax_rate": Decimal("10.00"),
        "version": 1,
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return values


def _payment_values(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "invoice_id": 1,
        "method": "card",
        "status": "approved",
        "amount": Decimal("327.80"),
        "reference": None,
        "card_last4": "4242",
        "reason": None,
        "created_at": NOW,
    }
    values.update(overrides)
    return values


def _rejects(db: Connection, statement: Any, constraint: str) -> None:
    with pytest.raises(IntegrityError) as info:
        db.execute(statement)
    assert constraint in str(info.value)
    db.rollback()


def test_a_second_invoice_for_an_order_is_rejected(
    db: Connection, postgres_invoice_store: PostgresInvoiceStore
) -> None:
    _rejects(
        db,
        insert(invoices).values(**_invoice_values(order_id=3, order_number="PED-0003")),
        "invoices_order_key",
    )


def test_a_repeated_invoice_number_is_rejected(
    db: Connection, postgres_invoice_store: PostgresInvoiceStore
) -> None:
    _rejects(
        db,
        insert(invoices).values(**_invoice_values(number="FAC-0001")),
        "invoices_number_key",
    )


def test_an_unknown_invoice_status_is_rejected(
    db: Connection, postgres_invoice_store: PostgresInvoiceStore
) -> None:
    _rejects(
        db,
        insert(invoices).values(**_invoice_values(status="lost")),
        "ck_invoices_status",
    )


def test_a_card_last4_with_letters_is_rejected(
    db: Connection, postgres_invoice_store: PostgresInvoiceStore
) -> None:
    _rejects(
        db,
        insert(payments).values(**_payment_values(card_last4="42ab")),
        "ck_payments_card_last4",
    )


def test_an_unknown_payment_method_is_rejected(
    db: Connection, postgres_invoice_store: PostgresInvoiceStore
) -> None:
    _rejects(
        db,
        insert(payments).values(**_payment_values(method="crypto")),
        "ck_payments_method",
    )


def test_a_second_approved_payment_for_an_invoice_is_rejected(
    db: Connection, postgres_invoice_store: PostgresInvoiceStore
) -> None:
    db.execute(insert(payments).values(**_payment_values()))

    _rejects(
        db,
        insert(payments).values(**_payment_values()),
        "uq_payments_one_approved_per_invoice",
    )


def test_declined_and_failed_payments_are_allowed_next_to_an_approved_one(
    db: Connection, postgres_invoice_store: PostgresInvoiceStore
) -> None:
    db.execute(
        insert(payments).values(
            [
                _payment_values(),
                _payment_values(
                    status="declined",
                    card_last4="0002",
                    reason="CARD_DECLINED",
                ),
                _payment_values(
                    status="failed",
                    card_last4="0003",
                    reason="GATEWAY_UNAVAILABLE",
                ),
            ]
        )
    )

    approved = db.execute(
        select(func.count())
        .select_from(payments)
        .where(payments.c.invoice_id == 1, payments.c.status == "approved")
    ).scalar_one()
    assert approved == 1
