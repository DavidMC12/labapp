"""Idempotency and state guarantees of the PostgreSQL invoice store."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.errors import ApiError
from app.modules.invoices.adapters.postgres import PostgresInvoiceStore
from tests.invoices.contract_store import attempt, respond

NOW = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)


def _pay(
    store: PostgresInvoiceStore,
    invoice_id: int,
    key: str,
    fingerprint: str,
    *,
    amount: str,
):
    return store.register_payment(
        invoice_id,
        key=key,
        fingerprint=fingerprint,
        expected_version=None,
        attempt=attempt(amount=amount),
        respond=respond,
        now=NOW,
    )


def test_a_key_is_scoped_to_its_invoice(
    postgres_invoice_store: PostgresInvoiceStore,
) -> None:
    other = postgres_invoice_store.issue_invoice(2, None, NOW)

    first = _pay(postgres_invoice_store, 1, "shared-key", "fp-1", amount="327.80")
    second = _pay(
        postgres_invoice_store,
        other.id,
        "shared-key",
        "fp-1",
        amount="121.00",
    )

    assert first.replayed is False
    assert first.response.body["payment_id"] == 5
    assert second.replayed is False
    assert second.response.body["payment_id"] == 6
    assert second.response.body["invoice_status"] == "paid"


def test_a_void_invoice_is_not_payable_and_frees_the_key(
    postgres_invoice_store: PostgresInvoiceStore,
) -> None:
    postgres_invoice_store.void_for_order(3, NOW)

    with pytest.raises(ApiError) as error:
        _pay(postgres_invoice_store, 1, "key-void", "fp-1", amount="327.80")

    assert error.value.code == "INVOICE_NOT_PAYABLE"
    assert postgres_invoice_store.find_key(1, "key-void", NOW) is None
    assert len(postgres_invoice_store.get_invoice(1).payments) == 2
