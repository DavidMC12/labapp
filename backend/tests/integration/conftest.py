"""Fixtures for the PostgreSQL integration tests.

The directory is skipped unless ``TEST_DATABASE_URL`` is set in the process
environment. It must point to a direct, unpooled database: the tests create a
random schema, run the migrations there and drop the schema afterwards.
"""

from __future__ import annotations

import os
import re
import secrets
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine
from sqlalchemy.pool import NullPool

from app.config import Settings
from app.infra.db import create_db_engine, normalize_database_url

BACKEND_DIR = Path(__file__).resolve().parents[2]
ALEMBIC_INI = BACKEND_DIR / "migrations" / "alembic.ini"
_SCHEMA_PATTERN = re.compile(r"t_[0-9a-f]{16}")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip this directory as a whole when no test database is configured."""
    if os.environ.get("TEST_DATABASE_URL"):
        return
    skip = pytest.mark.skip(reason="TEST_DATABASE_URL is not set")
    directory = Path(__file__).resolve().parent
    for item in items:
        if Path(str(item.path)).resolve().is_relative_to(directory):
            item.add_marker(skip)


def _test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        raise RuntimeError("TEST_DATABASE_URL is not set")
    return url


def _alembic_config(settings: Settings) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.attributes["settings"] = settings
    return config


def _bootstrap_engine(settings: Settings) -> Engine:
    assert settings.database_url is not None
    return create_engine(
        normalize_database_url(settings.database_url),
        poolclass=NullPool,
        hide_parameters=True,
    )


@pytest.fixture(scope="session")
def database_schema() -> str:
    return f"t_{secrets.token_hex(8)}"


@pytest.fixture(scope="session")
def database_settings(database_schema: str) -> Settings:
    url = _test_database_url()
    return Settings(
        database_url=url,
        database_url_unpooled=url,
        database_schema=database_schema,
    )


@pytest.fixture(scope="session")
def alembic_config(database_settings: Settings) -> Config:
    return _alembic_config(database_settings)


@pytest.fixture(scope="session")
def database_engine(database_settings: Settings, database_schema: str) -> Iterator[Engine]:
    bootstrap = _bootstrap_engine(database_settings)
    quoted_schema = bootstrap.dialect.identifier_preparer.quote_schema(database_schema)
    with bootstrap.connect() as connection:
        connection.exec_driver_sql(f"CREATE SCHEMA {quoted_schema}")
        connection.commit()

    engine: Engine | None = None
    try:
        command.upgrade(_alembic_config(database_settings), "head")
        engine = create_db_engine(database_settings, pin_search_path=True)
        yield engine
    finally:
        if engine is not None:
            engine.dispose()
        with bootstrap.connect() as connection:
            if _SCHEMA_PATTERN.fullmatch(database_schema):
                connection.exec_driver_sql(f"DROP SCHEMA {quoted_schema} CASCADE")
                connection.commit()
        bootstrap.dispose()


@pytest.fixture(scope="session")
def unpinned_database_engine(database_settings: Settings) -> Iterator[Engine]:
    """An engine with the schema translate map but no pinned search path.

    Raw SQL that forgets to qualify its table resolves in ``public`` and fails.
    """
    engine = create_db_engine(database_settings)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db(database_engine: Engine, database_schema: str) -> Iterator[Connection]:
    with database_engine.connect() as connection:
        current = connection.exec_driver_sql("select current_schema()").scalar_one()
        assert current == database_schema
        connection.exec_driver_sql(
            "TRUNCATE TABLE users, sessions, customers RESTART IDENTITY CASCADE"
        )
        connection.commit()
        try:
            yield connection
        finally:
            connection.rollback()
