"""PostgreSQL implementations of the test-only control stores."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.engine import Connection, Engine

from app.infra.db import qualified_table_name
from app.modules.orders.tables import settings as settings_table

CLOCK_OFFSET_KEY = "clock_offset_seconds"


@contextmanager
def _using(engine: Engine, connection: Connection | None) -> Iterator[Connection]:
    """Use the caller's transaction, or open and commit one of our own."""
    if connection is not None:
        yield connection
        return
    with engine.begin() as opened:
        yield opened


class PostgresClockOffsetStore:
    """Store the clock offset in the ``settings`` table."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @staticmethod
    def _read(connection: Connection) -> float:
        value = connection.execute(
            select(settings_table.c.value).where(settings_table.c.key == CLOCK_OFFSET_KEY)
        ).scalar_one_or_none()
        return 0.0 if value is None else float(value)

    def get(self, *, connection: Connection | None = None) -> float:
        with _using(self._engine, connection) as active:
            return self._read(active)

    def set(self, seconds: float, *, connection: Connection | None = None) -> None:
        with _using(self._engine, connection) as active:
            self._write(active, seconds)

    def _write(self, connection: Connection, seconds: float) -> None:
        value = str(float(seconds))
        statement = postgres_insert(settings_table).values(
            key=CLOCK_OFFSET_KEY,
            value=value,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[settings_table.c.key],
            set_={"value": statement.excluded.value},
        )
        connection.execute(statement)

    def advance(self, seconds: float, *, connection: Connection | None = None) -> float:
        with _using(self._engine, connection) as active:
            return self._advance(active, seconds)

    def _advance(self, connection: Connection, seconds: float) -> float:
        table = qualified_table_name(self._engine, settings_table)
        delta = float(seconds)
        updated = connection.execute(
            text(
                f"UPDATE {table} SET value = (value::float8 + :delta)::text "
                f"WHERE key = '{CLOCK_OFFSET_KEY}' RETURNING value"
            ),
            {"delta": delta},
        ).scalar_one_or_none()
        if updated is not None:
            return float(updated)

        inserted = connection.execute(
            text(
                f"INSERT INTO {table} (key, value) "
                f"VALUES ('{CLOCK_OFFSET_KEY}', CAST(:delta AS float8)::text) "
                "ON CONFLICT (key) DO UPDATE SET value = (value::float8 + :delta)::text "
                "RETURNING value"
            ),
            {"delta": delta},
        ).scalar_one()
        return float(inserted)


__all__ = ["PostgresClockOffsetStore"]
