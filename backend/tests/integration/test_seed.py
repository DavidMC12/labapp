"""The seed command against PostgreSQL."""

from __future__ import annotations

from sqlalchemy import Connection, select

from app.cli import seed_database
from app.config import Settings
from app.modules.auth.tables import users
from app.modules.customers.tables import customers


def _snapshot(connection: Connection) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    user_rows = [
        dict(row) for row in connection.execute(select(users).order_by(users.c.id)).mappings()
    ]
    customer_rows = [
        dict(row)
        for row in connection.execute(select(customers).order_by(customers.c.id)).mappings()
    ]
    return user_rows, customer_rows


def test_seed_is_idempotent(db: Connection, database_settings: Settings) -> None:
    seed_database(database_settings)
    first = _snapshot(db)

    seed_database(database_settings)
    second = _snapshot(db)

    assert first == second
    assert len(first[0]) == 4
    assert len(first[1]) == 10
