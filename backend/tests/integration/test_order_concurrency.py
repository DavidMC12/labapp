"""Concurrency behavior of the PostgreSQL order store."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier

import pytest
from sqlalchemy import Engine, update

from app.domain.orders import OrderAction, OrderStatus
from app.errors import ApiError
from app.modules.customers.tables import customers
from app.modules.orders.adapters.postgres import PostgresOrderStore
from app.modules.orders.ports import CustomerInactive, VersionConflict

NOW = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)


def _confirm(store: PostgresOrderStore, order_id: int) -> str:
    try:
        store.transition(order_id, OrderAction.CONFIRM, None, NOW)
    except ApiError as error:
        if error.code == "INSUFFICIENT_STOCK":
            return "shortage"
        raise
    return "confirmed"


def test_twenty_concurrent_creates_never_repeat_a_number(
    order_store: PostgresOrderStore,
) -> None:
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(order_store.create_order, 1, NOW) for _ in range(20)]
        created = [future.result(timeout=20) for future in futures]

    numbers = [order.number for order in created]
    assert len(set(numbers)) == 20
    assert set(numbers) == {f"PED-{value:04d}" for value in range(8, 28)}
    assert len({order.id for order in created}) == 20


def test_two_confirms_of_the_same_order_finish_with_one_winner(
    order_store: PostgresOrderStore,
) -> None:
    barrier = Barrier(2)

    def confirm() -> str:
        barrier.wait()
        try:
            order_store.transition(1, OrderAction.CONFIRM, 1, NOW)
        except VersionConflict:
            return "conflict"
        return "confirmed"

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(confirm) for _ in range(2)]
        outcomes = [future.result(timeout=15) for future in futures]

    assert sorted(outcomes) == ["confirmed", "conflict"]
    assert order_store.get_order(1).version == 2
    assert order_store.get_product(1).stock == 118


def test_two_orders_for_the_last_units_finish_with_one_winner(
    order_store: PostgresOrderStore,
) -> None:
    first = order_store.create_order(1, NOW)
    second = order_store.create_order(2, NOW)
    order_store.add_line(first.id, 7, 2, None, NOW)
    order_store.add_line(second.id, 7, 2, None, NOW)
    barrier = Barrier(2)

    def confirm(order_id: int) -> str:
        barrier.wait()
        return _confirm(order_store, order_id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(confirm, first.id),
            executor.submit(confirm, second.id),
        ]
        outcomes = [future.result(timeout=15) for future in futures]

    assert sorted(outcomes) == ["confirmed", "shortage"]
    assert order_store.get_product(7).stock == 1


def test_opposite_line_order_does_not_deadlock(
    order_store: PostgresOrderStore,
) -> None:
    first = order_store.create_order(1, NOW)
    second = order_store.create_order(2, NOW)
    order_store.add_line(first.id, 1, 1, None, NOW)
    order_store.add_line(first.id, 2, 1, None, NOW)
    order_store.add_line(second.id, 2, 1, None, NOW)
    order_store.add_line(second.id, 1, 1, None, NOW)
    barrier = Barrier(2)

    def confirm(order_id: int) -> str:
        barrier.wait()
        return _confirm(order_store, order_id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(confirm, first.id),
            executor.submit(confirm, second.id),
        ]
        outcomes = [future.result(timeout=15) for future in futures]

    assert sorted(outcomes) == ["confirmed", "confirmed"]
    assert order_store.get_product(1).stock == 118
    assert order_store.get_product(2).stock == 193


def test_cancel_and_confirm_of_the_same_product_keep_stock_consistent(
    order_store: PostgresOrderStore,
) -> None:
    order_store.transition(1, OrderAction.CONFIRM, None, NOW)
    other = order_store.create_order(2, NOW)
    order_store.add_line(other.id, 1, 1, None, NOW)
    barrier = Barrier(2)

    def cancel() -> None:
        barrier.wait()
        order_store.transition(1, OrderAction.CANCEL, None, NOW)

    def confirm() -> None:
        barrier.wait()
        order_store.transition(other.id, OrderAction.CONFIRM, None, NOW)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(cancel), executor.submit(confirm)]
        for future in futures:
            future.result(timeout=15)

    assert order_store.get_product(1).stock == 119
    assert order_store.get_order(1).status == OrderStatus.CANCELLED
    assert order_store.get_order(other.id).status == OrderStatus.CONFIRMED


def test_a_deactivation_cannot_slip_past_confirm(
    order_store: PostgresOrderStore,
    unpinned_database_engine: Engine,
) -> None:
    order = order_store.create_order(1, NOW)
    order_store.add_line(order.id, 1, 1, None, NOW)

    with unpinned_database_engine.connect() as blocker:
        blocker.execute(update(customers).where(customers.c.id == 1).values(status="inactive"))
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                order_store.transition,
                order.id,
                OrderAction.CONFIRM,
                None,
                NOW,
            )
            time.sleep(0.2)
            blocker.commit()
            with pytest.raises(CustomerInactive):
                future.result(timeout=15)

    assert order_store.get_order(order.id).status == OrderStatus.DRAFT
    assert order_store.get_product(1).stock == 120
