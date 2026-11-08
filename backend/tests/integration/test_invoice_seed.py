"""The seed command and replace_all against PostgreSQL invoices."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import Connection, Engine, func, select

from app.cli import seed_database
from app.config import Settings
from app.modules.customers.adapters.postgres import PostgresCustomerRepository
from app.modules.invoices.adapters.postgres import PostgresInvoiceStore
from app.modules.invoices.gateway import FakeGateway
from app.modules.invoices.models import PaymentAttempt, StoredResponse
from app.modules.invoices.seed import seed_invoices, seed_payments
from app.modules.invoices.tables import idempotency_keys, invoice_lines, invoices, payments
from app.modules.orders.adapters.postgres import PostgresOrderStore
from app.modules.orders.tables import orders

NOW = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)


def _rows(connection: Connection, table: object) -> list[dict[str, object]]:
    return [
        dict(row)
        for row in connection.execute(
            select(table).order_by(*table.primary_key.columns)  # type: ignore[attr-defined]
        ).mappings()
    ]


def _snapshot(connection: Connection) -> tuple[list[dict[str, object]], ...]:
    return (
        _rows(connection, invoices),
        _rows(connection, invoice_lines),
        _rows(connection, payments),
        _rows(connection, idempotency_keys),
        _rows(connection, orders),
    )


def _count(connection: Connection, table: object) -> int:
    return connection.execute(select(func.count()).select_from(table)).scalar_one()  # type: ignore[arg-type]


def test_the_seed_loads_the_invoices_and_is_idempotent(
    db: Connection, database_settings: Settings
) -> None:
    seed_database(database_settings)
    first = _snapshot(db)

    seed_database(database_settings)

    assert first == _snapshot(db)
    assert len(first[0]) == 3
    assert len(first[1]) == 3
    assert len(first[2]) == 4
    assert first[3] == []


def test_the_seed_links_orders_3_4_and_5_without_bumping_them(
    db: Connection,
    database_settings: Settings,
    unpinned_database_engine: Engine,
) -> None:
    seed_database(database_settings)
    store = PostgresOrderStore(unpinned_database_engine)

    for order_id, invoice_id in ((3, 1), (4, 2), (5, 3)):
        order = store.get_order(order_id)
        assert order.invoice_id == invoice_id
        assert order.version == 1
        assert order.updated_at == order.created_at


def test_the_seed_continues_with_invoice_four_and_payment_five(
    db: Connection,
    database_settings: Settings,
    unpinned_database_engine: Engine,
) -> None:
    seed_database(database_settings)
    store = PostgresInvoiceStore(unpinned_database_engine, FakeGateway())

    invoice = store.issue_invoice(2, None, NOW)
    outcome = store.register_payment(
        invoice.id,
        key="key-1",
        fingerprint="fp-1",
        expected_version=None,
        attempt=PaymentAttempt("cash", invoice.total, None, None),
        respond=lambda payment, after: StoredResponse(201, {"payment_id": payment.id}),
        now=NOW + timedelta(minutes=1),
    )

    assert invoice.number == "FAC-0004"
    assert outcome.response.body["payment_id"] == 5
    assert store.get_invoice(invoice.id).payments[-1].id == 5


def test_the_seed_adds_the_invoices_when_only_they_are_missing(
    db: Connection,
    database_settings: Settings,
    unpinned_database_engine: Engine,
) -> None:
    seed_database(database_settings)
    store = PostgresInvoiceStore(unpinned_database_engine, FakeGateway())
    store.replace_all([], [])

    seed_database(database_settings)

    orders_store = PostgresOrderStore(unpinned_database_engine)
    assert orders_store.get_order(3).invoice_id == 1
    assert orders_store.get_order(3).version == 1
    assert _count(db, invoices) == 3


def test_replace_all_twice_keeps_the_links(
    db: Connection, postgres_invoice_store: PostgresInvoiceStore
) -> None:
    postgres_invoice_store.replace_all(seed_invoices(), seed_payments())
    postgres_invoice_store.replace_all(seed_invoices(), seed_payments())

    assert _count(db, invoices) == 3
    assert _count(db, invoice_lines) == 3
    assert _count(db, payments) == 4


def test_an_empty_replace_all_follows_the_reset_order(
    db: Connection,
    postgres_invoice_store: PostgresInvoiceStore,
    postgres_order_store: PostgresOrderStore,
    order_customers: PostgresCustomerRepository,
) -> None:
    postgres_invoice_store.replace_all([], [])
    postgres_order_store.replace_all([], [], Decimal("10.00"))
    order_customers.replace_all([])

    assert _count(db, invoices) == 0
    assert _count(db, invoice_lines) == 0
    assert _count(db, payments) == 0
    assert _count(db, idempotency_keys) == 0
    assert _count(db, orders) == 0
