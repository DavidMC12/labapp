from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import psycopg
import pytest
from sqlalchemy.pool import NullPool

from app.config import Settings
from app.infra.db import as_utc, create_db_engine, normalize_database_url

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
