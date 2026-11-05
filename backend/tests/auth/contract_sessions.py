"""Reusable behavioral tests for SessionStore adapters."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.modules.auth.models import Session

NOW = datetime(2026, 1, 1, 8, 0, tzinfo=UTC)


def session(
    token_hash: str = "token-hash",
    when: datetime = NOW,
    user_id: int = 1,
) -> Session:
    """Build a session for the contract tests."""
    return Session(
        token_hash=token_hash,
        user_id=user_id,
        created_at=when,
        last_seen_at=when,
    )


class SessionStoreContract:
    """The behavior every SessionStore adapter must share.

    A concrete test class provides ``session_store`` (a fresh store) and
    ``session_store_factory`` (a callable that builds a fresh store with a cap).
    """

    @pytest.fixture
    def session_store(self) -> Any:
        raise NotImplementedError

    @pytest.fixture
    def session_store_factory(self) -> Callable[[int], Any]:
        raise NotImplementedError

    def test_create_and_get_a_session(self, session_store: Any) -> None:
        stored = session()

        session_store.create(stored)

        assert session_store.get("token-hash") == stored

    def test_get_an_unknown_session_returns_none(self, session_store: Any) -> None:
        assert session_store.get("missing") is None

    def test_touch_updates_an_existing_session(self, session_store: Any) -> None:
        session_store.create(session())
        later = NOW + timedelta(minutes=5)

        session_store.touch("token-hash", later)

        stored = session_store.get("token-hash")
        assert stored is not None
        assert stored.last_seen_at == later

    def test_touch_is_monotonic(self, session_store: Any) -> None:
        session_store.create(session())
        later = NOW + timedelta(minutes=5)
        session_store.touch("token-hash", later)

        session_store.touch("token-hash", NOW + timedelta(minutes=1))

        stored = session_store.get("token-hash")
        assert stored is not None
        assert stored.last_seen_at == later

    def test_touch_on_an_unknown_key_is_a_noop(self, session_store: Any) -> None:
        session_store.touch("missing", NOW)

        assert session_store.get("missing") is None

    def test_touch_does_not_resurrect_a_deleted_session(self, session_store: Any) -> None:
        session_store.create(session())
        session_store.delete("token-hash")

        session_store.touch("token-hash", NOW + timedelta(minutes=1))

        assert session_store.get("token-hash") is None

    def test_delete_removes_a_session_and_ignores_unknown_keys(
        self,
        session_store: Any,
    ) -> None:
        session_store.create(session())

        session_store.delete("missing")
        assert session_store.get("token-hash") is not None

        session_store.delete("token-hash")
        assert session_store.get("token-hash") is None

        session_store.delete("token-hash")

    def test_purge_uses_a_strict_cutoff(self, session_store: Any) -> None:
        session_store.create(session("old", NOW - timedelta(seconds=1)))
        session_store.create(session("boundary", NOW))
        session_store.create(session("recent", NOW + timedelta(seconds=1)))

        removed = session_store.purge_older_than(NOW)

        assert removed == 1
        assert session_store.get("old") is None
        assert session_store.get("boundary") is not None
        assert session_store.get("recent") is not None

    def test_purge_returns_zero_when_nothing_is_old_enough(
        self,
        session_store: Any,
    ) -> None:
        session_store.create(session("boundary", NOW))

        assert session_store.purge_older_than(NOW) == 0
        assert session_store.get("boundary") is not None

    def test_capacity_evicts_the_sessions_with_the_oldest_last_seen(
        self,
        session_store_factory: Callable[[int], Any],
    ) -> None:
        session_store = session_store_factory(3)
        session_store.create(session("first", NOW + timedelta(seconds=10)))
        session_store.create(session("oldest", NOW + timedelta(seconds=1)))
        session_store.create(session("middle", NOW + timedelta(seconds=5)))

        session_store.create(session("new", NOW + timedelta(seconds=20)))

        assert session_store.get("oldest") is None
        assert session_store.get("first") is not None
        assert session_store.get("middle") is not None
        assert session_store.get("new") is not None
