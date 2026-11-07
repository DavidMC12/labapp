"""Database engine, metadata and URL helpers."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import psycopg
from sqlalchemy import MetaData, Sequence, Table, create_engine, event
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.pool import NullPool

from app.config import Settings

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)

_PSYCOPG_PREFIX = "postgresql+psycopg://"
_ACCEPTED_PREFIXES = (_PSYCOPG_PREFIX, "postgresql://", "postgres://")


def normalize_database_url(url: str) -> str:
    """Return the URL in the form SQLAlchemy uses for psycopg 3.

    Query parameters such as ``sslmode`` and ``channel_binding`` are kept as they are.
    """
    for prefix in _ACCEPTED_PREFIXES:
        if url.startswith(prefix):
            return _PSYCOPG_PREFIX + url[len(prefix) :]
    raise ValueError("Unsupported database URL")


def create_db_engine(settings: Settings, *, pin_search_path: bool = False) -> Engine:
    """Build a lazy engine for the configured database.

    Each serverless instance talks to the provider's pooler, so the engine keeps no
    connections of its own. Creating it never opens a connection.
    """
    if settings.database_url is None:
        raise RuntimeError("Database is not configured")

    schema = settings.database_schema
    if pin_search_path and schema is None:
        raise ValueError("pin_search_path requires a database schema")

    connect_args: dict[str, Any] = {"prepare_threshold": None}
    if pin_search_path:
        connect_args["options"] = f"-c search_path={schema}"

    engine = create_engine(
        normalize_database_url(settings.database_url),
        poolclass=NullPool,
        hide_parameters=True,
        connect_args=connect_args,
    )
    event.listen(engine, "begin", _lock_timeout_setter(settings.lock_timeout_ms))
    if schema is not None:
        engine = engine.execution_options(schema_translate_map={None: schema})
    return engine


def _lock_timeout_setter(milliseconds: int) -> Callable[[Connection], None]:
    """Build the ``begin`` listener that bounds every lock wait of a transaction.

    ``SET LOCAL`` lasts until the transaction ends, so it also works behind a
    transaction-mode pooler, where a startup option or a plain ``SET`` would not. The
    value is an integer validated by ``Settings``, so formatting it in is safe.
    """
    statement = f"SET LOCAL lock_timeout = {int(milliseconds)}"

    def set_lock_timeout(connection: Connection) -> None:
        connection.exec_driver_sql(statement)

    return set_lock_timeout


def is_lock_timeout(error: BaseException) -> bool:
    """Tell whether the error is PostgreSQL giving up on a lock wait (SQLSTATE 55P03)."""
    original = getattr(error, "orig", error)
    return isinstance(original, psycopg.errors.LockNotAvailable)


def as_utc(value: datetime) -> datetime:
    """Return a driver timestamp as an aware UTC datetime."""
    return value.astimezone(UTC)


def qualified_table_name(engine: Engine, table: Table) -> str:
    """Return the table name for raw SQL, with the schema when one is configured.

    ``schema_translate_map`` only rewrites ``Table`` constructs, so raw SQL that
    names a table must receive the translated schema explicitly.
    """
    preparer = engine.dialect.identifier_preparer
    translate_map = engine.get_execution_options().get("schema_translate_map") or {}
    schema = translate_map.get(None)
    if schema is None:
        return preparer.quote(table.name)
    return f"{preparer.quote_schema(schema)}.{preparer.quote(table.name)}"


def qualified_sequence_name(engine: Engine, sequence: Sequence) -> str:
    """Return the sequence name for raw SQL, with the schema when one is configured."""
    preparer = engine.dialect.identifier_preparer
    translate_map = engine.get_execution_options().get("schema_translate_map") or {}
    schema = translate_map.get(None)
    name = preparer.quote(sequence.name)
    if schema is None:
        return name
    return f"{preparer.quote_schema(schema)}.{name}"


def unique_violation_of(error: BaseException, constraint_name: str) -> bool:
    """Tell whether the error is a unique violation of exactly that constraint."""
    original = getattr(error, "orig", None)
    if not isinstance(original, psycopg.errors.UniqueViolation):
        return False
    return original.diag.constraint_name == constraint_name
