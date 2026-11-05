"""Alembic environment for the LabApp database."""

from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

import app.modules.auth.tables  # noqa: F401
import app.modules.customers.tables  # noqa: F401
from app.config import Settings
from app.infra.db import metadata, normalize_database_url

target_metadata = metadata


def _settings() -> Settings:
    provided = context.config.attributes.get("settings")
    if provided is not None:
        return provided
    return Settings()


def _database_url(settings: Settings) -> str:
    url = settings.database_url_unpooled
    if url is None:
        if settings.database_schema is not None:
            raise RuntimeError("DATABASE_URL_UNPOOLED is required with DATABASE_SCHEMA")
        url = settings.database_url
    if url is None:
        raise RuntimeError("Database is not configured")
    return normalize_database_url(url)


def run_migrations_online() -> None:
    """Run the migrations through a plain engine, never the application one."""
    settings = _settings()
    schema = settings.database_schema
    engine = create_engine(
        _database_url(settings),
        poolclass=NullPool,
        hide_parameters=True,
    )
    with engine.connect() as connection:
        if schema is not None:
            quoted_schema = engine.dialect.identifier_preparer.quote_schema(schema)
            connection.exec_driver_sql(f"SET search_path TO {quoted_schema}")
            connection.commit()
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations_online()
