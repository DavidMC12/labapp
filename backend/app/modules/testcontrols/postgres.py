"""PostgreSQL implementations of the test-only control stores."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

from sqlalchemy import case, delete, func, insert, null, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.engine import Connection, Engine

from app.infra.db import qualified_table_name
from app.modules.orders.tables import settings as settings_table
from app.modules.testcontrols.models import FaultDecision, NewRule, Rule
from app.modules.testcontrols.ports import MAX_FAULT_RULES, TooManyFaultRules
from app.modules.testcontrols.tables import fault_rules

CLOCK_OFFSET_KEY = "clock_offset_seconds"
FAULT_RULES_LOCK_KEY = 7_239_015


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


def _active_condition():
    remaining = fault_rules.c.remaining
    return or_(remaining.is_(None), remaining > 0)


def _rule_from_row(row: Mapping[str, Any]) -> Rule:
    return Rule(
        id=row["id"],
        target=row["target"],
        method=row["method"],
        path=row["path"],
        latency_ms=row["latency_ms"],
        status=row["status"],
        remaining=row["remaining"],
    )


class PostgresFaultStore:
    """Store the fault rules in PostgreSQL."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(self, rule: NewRule) -> Rule:
        with self._engine.begin() as connection:
            connection.execute(
                text("select pg_advisory_xact_lock(:key)"),
                {"key": FAULT_RULES_LOCK_KEY},
            )
            connection.execute(delete(fault_rules).where(fault_rules.c.remaining == 0))
            active = connection.execute(
                select(func.count()).select_from(fault_rules).where(_active_condition())
            ).scalar_one()
            if active >= MAX_FAULT_RULES:
                raise TooManyFaultRules
            row = (
                connection.execute(
                    insert(fault_rules)
                    .values(
                        target=rule.target,
                        method=rule.method,
                        path=rule.path,
                        latency_ms=rule.latency_ms,
                        status=rule.status,
                        remaining=rule.remaining,
                    )
                    .returning(*fault_rules.c)
                )
                .mappings()
                .one()
            )
        return _rule_from_row(row)

    def list(self) -> list[Rule]:
        with self._engine.begin() as connection:
            rows = (
                connection.execute(
                    select(fault_rules).where(_active_condition()).order_by(fault_rules.c.id)
                )
                .mappings()
                .all()
            )
        return [_rule_from_row(row) for row in rows]

    def clear(self) -> None:
        with self._engine.begin() as connection:
            connection.execute(delete(fault_rules))

    def take(
        self,
        method: str,
        path: str,
        *,
        connection: Connection | None = None,
    ) -> FaultDecision | None:
        condition = (
            fault_rules.c.target == "route",
            or_(fault_rules.c.method.is_(None), fault_rules.c.method == method),
            fault_rules.c.path == path,
            _active_condition(),
        )
        return self._consume(condition, connection)

    def take_gateway(self, *, connection: Connection | None = None) -> FaultDecision | None:
        condition = (fault_rules.c.target == "gateway", _active_condition())
        return self._consume(condition, connection)

    def _consume(
        self,
        condition: tuple[object, ...],
        connection: Connection | None,
    ) -> FaultDecision | None:
        with _using(self._engine, connection) as active:
            remaining = fault_rules.c.remaining
            candidate = (
                select(fault_rules.c.id)
                .where(*condition)
                .order_by(fault_rules.c.id)
                .limit(1)
                .with_for_update()
            )
            statement = (
                update(fault_rules)
                .where(fault_rules.c.id == candidate.scalar_subquery())
                .values(
                    remaining=case(
                        (remaining.is_(None), null()),
                        else_=remaining - 1,
                    )
                )
                .returning(fault_rules.c.latency_ms, fault_rules.c.status)
            )
            row = active.execute(statement).mappings().first()
        if row is None:
            return None
        return FaultDecision(row["latency_ms"], row["status"])


__all__ = ["PostgresClockOffsetStore", "PostgresFaultStore"]
