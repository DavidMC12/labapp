"""The seed command against PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Connection, Engine, select

from app.cli import seed_database
from app.config import Settings
from app.modules.auth.tables import users
from app.modules.customers.tables import customers
from app.modules.orders.adapters.postgres import PostgresOrderStore
from app.modules.orders.tables import order_lines, orders, products
from app.modules.orders.tables import settings as settings_table

NOW = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)


def _rows(connection: Connection, table: object) -> list[dict[str, object]]:
    return [
        dict(row)
        for row in connection.execute(select(table).order_by(table.c.id)).mappings()  # type: ignore[attr-defined]
    ]


def _snapshot(
    connection: Connection,
) -> tuple[list[dict[str, object]], ...]:
    settings_rows = [
        dict(row)
        for row in connection.execute(
            select(settings_table).order_by(settings_table.c.key)
        ).mappings()
    ]
    return (
        _rows(connection, users),
        _rows(connection, customers),
        _rows(connection, products),
        _rows(connection, orders),
        _rows(connection, order_lines),
        settings_rows,
    )


def test_seed_is_idempotent(db: Connection, database_settings: Settings) -> None:
    seed_database(database_settings)
    first = _snapshot(db)

    seed_database(database_settings)
    second = _snapshot(db)

    assert first == second
    assert len(first[0]) == 4
    assert len(first[1]) == 10
    assert len(first[2]) == 15
    assert len(first[3]) == 7
    assert len(first[4]) == 9
    assert first[5] == [{"key": "tax_rate", "value": "10.00"}]


def test_seed_continues_the_sequences(
    db: Connection,
    database_settings: Settings,
    unpinned_database_engine: Engine,
) -> None:
    seed_database(database_settings)
    store = PostgresOrderStore(unpinned_database_engine)

    created = store.create_order(1, NOW)
    changed = store.add_line(created.id, 1, 1, None, NOW)

    assert created.number == "PED-0008"
    assert changed.lines[0].id == 10
