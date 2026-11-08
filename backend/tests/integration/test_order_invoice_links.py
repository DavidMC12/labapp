"""The order store's invoice helpers against PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.orders import OrderAction, OrderStatus
from app.errors import ApiError
from app.modules.invoices.adapters.postgres import PostgresInvoiceStore
from app.modules.orders.adapters.postgres import PostgresOrderStore
from app.modules.orders.ports import OrderNotFound

NOW = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)
LATER = datetime(2026, 2, 1, 13, 0, tzinfo=UTC)


def test_attach_invoice_links_it_and_bumps_the_version(
    postgres_order_store: PostgresOrderStore,
    postgres_invoice_store: PostgresInvoiceStore,
) -> None:
    changed = postgres_order_store.attach_invoice(2, 1, LATER)

    assert changed.invoice_id == 1
    assert changed.version == 2
    assert changed.updated_at == LATER
    assert postgres_order_store.get_order(2).invoice_id == 1


def test_attach_invoice_rejects_an_unknown_order(
    postgres_order_store: PostgresOrderStore,
) -> None:
    with pytest.raises(OrderNotFound):
        postgres_order_store.attach_invoice(99, 1, LATER)


def test_mark_paid_moves_a_confirmed_order(
    postgres_order_store: PostgresOrderStore,
) -> None:
    changed = postgres_order_store.mark_paid(2, LATER)

    assert changed.status == OrderStatus.PAID
    assert changed.version == 2
    assert changed.updated_at == LATER


def test_mark_paid_rejects_another_state(postgres_order_store: PostgresOrderStore) -> None:
    with pytest.raises(ApiError) as error:
        postgres_order_store.mark_paid(1, LATER)

    assert error.value.code == "INVALID_TRANSITION"


def test_link_invoices_keeps_every_version_and_timestamp(
    postgres_order_store: PostgresOrderStore,
    postgres_invoice_store: PostgresInvoiceStore,
) -> None:
    postgres_order_store.link_invoices({2: 1})

    assert postgres_order_store.get_order(2).invoice_id == 1
    assert postgres_order_store.get_order(3).invoice_id is None
    for order_id in range(1, 8):
        order = postgres_order_store.get_order(order_id)
        assert order.version == 1
        assert order.updated_at == order.created_at


def test_cancelling_a_confirmed_order_voids_its_invoice(
    postgres_order_store: PostgresOrderStore,
    postgres_invoice_store: PostgresInvoiceStore,
) -> None:
    changed = postgres_order_store.transition(3, OrderAction.CANCEL, None, LATER)

    invoice = postgres_invoice_store.get_invoice(1)
    assert changed.status == OrderStatus.CANCELLED
    assert invoice.status.value == "void"
    assert invoice.version == 2
    assert invoice.updated_at == LATER


def test_cancelling_a_draft_does_not_touch_an_invoice(
    postgres_order_store: PostgresOrderStore,
    postgres_invoice_store: PostgresInvoiceStore,
) -> None:
    postgres_order_store.transition(1, OrderAction.CANCEL, None, LATER)

    assert postgres_invoice_store.get_invoice(1).status.value == "issued"
    assert postgres_order_store.get_order(3).status == OrderStatus.CONFIRMED
