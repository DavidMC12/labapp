"""Tests for the invoice-related additions of the in-memory order store."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.domain.orders import OrderAction, OrderStatus
from app.errors import ApiError
from app.modules.customers.adapters.memory import InMemoryCustomerRepository
from app.modules.customers.seed import seed_customers
from app.modules.orders.adapters.memory import InMemoryOrderStore
from app.modules.orders.ports import OrderNotFound
from app.modules.orders.seed import seed_orders, seed_products

NOW = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)
LATER = NOW + timedelta(minutes=1)


@pytest.fixture
def store() -> InMemoryOrderStore:
    result = InMemoryOrderStore(InMemoryCustomerRepository(seed_customers()))
    result.replace_all(seed_products(), seed_orders(), Decimal("10.00"))
    return result


def test_attach_invoice_links_it_and_bumps_the_version(store: InMemoryOrderStore) -> None:
    changed = store.attach_invoice(2, 4, LATER)

    assert changed.invoice_id == 4
    assert changed.version == 2
    assert changed.updated_at == LATER
    assert store.get_order(2) == changed


def test_attach_invoice_rejects_an_unknown_order(store: InMemoryOrderStore) -> None:
    with pytest.raises(OrderNotFound):
        store.attach_invoice(99, 4, LATER)


def test_mark_paid_moves_a_confirmed_order(store: InMemoryOrderStore) -> None:
    changed = store.mark_paid(2, LATER)

    assert changed.status == OrderStatus.PAID
    assert changed.version == 2
    assert changed.updated_at == LATER
    assert store.get_order(2) == changed


def test_mark_paid_rejects_another_state(store: InMemoryOrderStore) -> None:
    with pytest.raises(ApiError) as error:
        store.mark_paid(1, LATER)

    assert error.value.code == "INVALID_TRANSITION"


def test_link_invoices_keeps_every_version_and_timestamp(store: InMemoryOrderStore) -> None:
    original = {id: store.get_order(id) for id in range(1, 8)}

    store.link_invoices({3: 1, 4: 2, 5: 3})

    expected = {1: None, 2: None, 3: 1, 4: 2, 5: 3, 6: None, 7: None}
    for order_id, invoice_id in expected.items():
        order = store.get_order(order_id)
        assert order is not None
        assert order.invoice_id == invoice_id
        assert order.version == 1
        assert order.updated_at == original[order_id].updated_at


class _RecordingInvoices:
    def __init__(self) -> None:
        self.calls: list[tuple[int, datetime]] = []

    def void_for_order(self, order_id: int, now: datetime) -> None:
        self.calls.append((order_id, now))


def test_cancelling_a_confirmed_order_voids_its_invoice(
    store: InMemoryOrderStore,
) -> None:
    invoices = _RecordingInvoices()
    store.invoices = invoices

    store.transition(2, OrderAction.CANCEL, None, LATER)

    assert invoices.calls == [(2, LATER)]


def test_cancelling_a_draft_does_not_void_an_invoice(store: InMemoryOrderStore) -> None:
    invoices = _RecordingInvoices()
    store.invoices = invoices

    store.transition(1, OrderAction.CANCEL, None, LATER)

    assert invoices.calls == []
