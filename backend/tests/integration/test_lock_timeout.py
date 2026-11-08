"""Every transaction bounds its lock waits, and the wait ends as a recognizable error."""

from __future__ import annotations

import time
from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import OperationalError

from app.config import Settings
from app.infra.db import create_db_engine, is_lock_timeout

LOCK_TIMEOUT_MS = 500


@pytest.fixture
def short_timeout_engine(database_settings: Settings, db: Connection) -> Iterator[Engine]:
    settings = database_settings.model_copy(update={"lock_timeout_ms": LOCK_TIMEOUT_MS})
    engine = create_db_engine(settings, pin_search_path=True)
    try:
        yield engine
    finally:
        engine.dispose()


def test_a_transaction_starts_with_the_configured_lock_timeout(
    short_timeout_engine: Engine,
) -> None:
    with short_timeout_engine.begin() as connection:
        assert connection.exec_driver_sql("SHOW lock_timeout").scalar_one() == "500ms"

    with short_timeout_engine.begin() as connection:
        assert connection.exec_driver_sql("SHOW lock_timeout").scalar_one() == "500ms"


def test_a_lock_wait_gives_up_and_is_recognized(short_timeout_engine: Engine) -> None:
    with short_timeout_engine.begin() as connection:
        connection.execute(text("INSERT INTO settings (key, value) VALUES ('probe', '1')"))

    with short_timeout_engine.begin() as holder:
        holder.execute(text("SELECT value FROM settings WHERE key = 'probe' FOR UPDATE"))

        started = time.monotonic()
        with pytest.raises(OperationalError) as caught:
            with short_timeout_engine.begin() as waiter:
                waiter.execute(text("SELECT value FROM settings WHERE key = 'probe' FOR UPDATE"))
        waited = time.monotonic() - started

    assert is_lock_timeout(caught.value)
    assert LOCK_TIMEOUT_MS / 1000 <= waited < 5

    with short_timeout_engine.begin() as connection:
        value = connection.execute(
            text("SELECT value FROM settings WHERE key = 'probe' FOR UPDATE")
        ).scalar_one()
    assert value == "1"
