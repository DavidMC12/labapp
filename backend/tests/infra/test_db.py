from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace

import psycopg
import pytest
from sqlalchemy import MetaData, Table
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool

from app.config import Settings
from app.infra.db import (
    as_utc,
    create_db_engine,
    normalize_database_url,
    qualified_table_name,
    unique_violation_of,
)
from app.modules.auth.tables import users

DATABASE_URL = "postgresql+psycopg://user:password@host/db"
SCHEMA = "t_0123456789abcdef"


@pytest.mark.parametrize(
    "url",
    [
        DATABASE_URL,
        "postgresql://user:password@host/db",
        "postgres://user:password@host/db",
    ],
)
def test_normalize_database_url_accepts_postgres_forms(url: str) -> None:
    assert normalize_database_url(url) == DATABASE_URL


@pytest.mark.parametrize(
    "query",
    ["sslmode=require", "sslmode=require&channel_binding=require", "options=-c%20search_path%3Dx"],
)
def test_normalize_database_url_keeps_query_parameters(query: str) -> None:
    assert normalize_database_url(f"postgresql://user:password@host/db?{query}") == (
        f"{DATABASE_URL}?{query}"
    )


@pytest.mark.parametrize(
    "url",
    [
        "mysql://user:password@host/db",
        "sqlite:///labapp.db",
        "postgresql+psycopg2://user:password@host/db",
        "http://user:password@host/db",
    ],
)
def test_normalize_database_url_rejects_other_forms(url: str) -> None:
    with pytest.raises(ValueError) as info:
        normalize_database_url(url)

    assert str(info.value) == "Unsupported database URL"
    assert "user:password" not in str(info.value)


def test_create_db_engine_requires_a_url() -> None:
    with pytest.raises(RuntimeError, match="Database is not configured"):
        create_db_engine(Settings())


def test_create_db_engine_is_lazy_and_keeps_no_connections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("create_db_engine opened a connection")

    monkeypatch.setattr(psycopg, "connect", unexpected_connect)

    engine = create_db_engine(Settings(database_url=DATABASE_URL))

    assert isinstance(engine.pool, NullPool)
    assert engine.pool.status() == "NullPool"
    assert engine.hide_parameters is True
    assert "schema_translate_map" not in engine.get_execution_options()


def test_create_db_engine_translates_the_schema() -> None:
    engine = create_db_engine(Settings(database_url=DATABASE_URL, database_schema=SCHEMA))

    assert engine.get_execution_options()["schema_translate_map"] == {None: SCHEMA}


def test_create_db_engine_refuses_to_pin_without_a_schema() -> None:
    with pytest.raises(ValueError, match="pin_search_path"):
        create_db_engine(Settings(database_url=DATABASE_URL), pin_search_path=True)


def test_as_utc_returns_an_aware_utc_datetime() -> None:
    local = datetime(2026, 1, 2, 3, 4, 5, 123456, tzinfo=timezone(timedelta(hours=-5)))

    converted = as_utc(local)

    assert converted == datetime(2026, 1, 2, 8, 4, 5, 123456, tzinfo=UTC)
    assert converted.tzinfo is UTC


def test_qualified_table_name_without_a_schema() -> None:
    engine = create_db_engine(Settings(database_url=DATABASE_URL))

    assert qualified_table_name(engine, users) == "users"


def test_qualified_table_name_with_a_schema() -> None:
    engine = create_db_engine(Settings(database_url=DATABASE_URL, database_schema=SCHEMA))

    assert qualified_table_name(engine, users) == f"{SCHEMA}.users"


def test_qualified_table_name_quotes_unsafe_identifiers() -> None:
    engine = create_db_engine(Settings(database_url=DATABASE_URL, database_schema=SCHEMA))
    table = Table("Order", MetaData())

    assert qualified_table_name(engine, table) == f'{SCHEMA}."Order"'


class _FakeUniqueViolation(psycopg.errors.UniqueViolation):
    diag = SimpleNamespace(constraint_name="users_email_lower_key")


def _integrity_error(original: BaseException) -> IntegrityError:
    return IntegrityError("INSERT INTO users ...", {"email": "leak@example.test"}, original)


def test_unique_violation_of_matches_the_constraint_name() -> None:
    error = _integrity_error(_FakeUniqueViolation("duplicate key"))

    assert unique_violation_of(error, "users_email_lower_key") is True
    assert unique_violation_of(error, "customers_email_lower_key") is False


def test_unique_violation_of_rejects_other_database_errors() -> None:
    error = _integrity_error(psycopg.errors.NotNullViolation("null value"))

    assert unique_violation_of(error, "users_email_lower_key") is False
    assert unique_violation_of(ValueError("not a database error"), "users_email_lower_key") is False


def test_create_db_engine_sets_a_lock_timeout_on_every_transaction() -> None:
    engine = create_db_engine(Settings(database_url=DATABASE_URL, lock_timeout_ms=1500))
    statements: list[str] = []

    class RecordingConnection:
        def exec_driver_sql(self, statement: str) -> None:
            statements.append(statement)

    listeners = list(engine.dispatch.begin)
    assert len(listeners) == 1
    listeners[0](RecordingConnection())

    assert statements == ["SET LOCAL lock_timeout = 1500"]


def test_create_db_engine_keeps_the_lock_timeout_on_the_schema_translated_engine() -> None:
    engine = create_db_engine(Settings(database_url=DATABASE_URL, database_schema=SCHEMA))

    assert len(list(engine.dispatch.begin)) == 1


def test_lock_timeout_setting_is_bounded() -> None:
    with pytest.raises(ValueError):
        Settings(lock_timeout_ms=99)
    with pytest.raises(ValueError):
        Settings(lock_timeout_ms=60001)
    assert Settings(lock_timeout_ms=100).lock_timeout_ms == 100
    assert Settings(lock_timeout_ms=60000).lock_timeout_ms == 60000


def test_is_lock_timeout_recognizes_only_the_lock_not_available_error() -> None:
    from sqlalchemy.exc import OperationalError

    from app.infra.db import is_lock_timeout

    assert is_lock_timeout(OperationalError("s", {}, psycopg.errors.LockNotAvailable("x")))
    assert is_lock_timeout(psycopg.errors.LockNotAvailable("x"))
    assert not is_lock_timeout(OperationalError("s", {}, psycopg.errors.DeadlockDetected("x")))
    assert not is_lock_timeout(ValueError("x"))


def test_is_deadlock_recognizes_only_the_deadlock_detected_error() -> None:
    from sqlalchemy.exc import OperationalError

    from app.infra.db import is_deadlock

    assert is_deadlock(OperationalError("s", {}, psycopg.errors.DeadlockDetected("x")))
    assert is_deadlock(psycopg.errors.DeadlockDetected("x"))
    assert not is_deadlock(OperationalError("s", {}, psycopg.errors.LockNotAvailable("x")))
    assert not is_deadlock(ValueError("x"))
