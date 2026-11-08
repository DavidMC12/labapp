"""Tests for the in-memory authentication adapters."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest

from app.domain.permissions import Role
from app.modules.auth.adapters.memory import (
    MAX_SESSIONS,
    InMemorySessionStore,
    InMemoryUserRepository,
)
from app.modules.auth.models import Session, User
from tests.auth.contract_sessions import SessionStoreContract
from tests.auth.contract_users import UserRepositoryContract

NOW = datetime(2026, 1, 1, 8, 0, tzinfo=UTC)


def _user(
    id: int = 1,
    name: str = "Admin Demo",
    email: str = "admin@labapp.test",
    role: Role = Role.ADMIN,
) -> User:
    return User(
        id=id,
        name=name,
        email=email,
        role=role,
        password_hash="hash",
        created_at=NOW,
    )


def _session(
    token_hash: str = "token-hash",
    when: datetime = NOW,
    user_id: int = 1,
) -> Session:
    return Session(
        token_hash=token_hash,
        user_id=user_id,
        created_at=when,
        last_seen_at=when,
    )


class TestInMemoryUserRepository(UserRepositoryContract):
    @pytest.fixture
    def user_repository(self) -> InMemoryUserRepository:
        return InMemoryUserRepository([_user()])

    def test_email_lookup_is_case_insensitive(self) -> None:
        repository = InMemoryUserRepository([_user()])

        assert repository.get_by_email("admin@labapp.test") == _user()
        assert repository.get_by_email("ADMIN@LABAPP.TEST") == _user()
        assert repository.get_by_email("  Admin@LabApp.Test  ") == _user()

    def test_concurrent_lookups_are_safe(self) -> None:
        user = _user()
        repository = InMemoryUserRepository([user])
        queries = ["ADMIN@LABAPP.TEST", "admin@labapp.test", "Admin@LabApp.Test"] * 50

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(repository.get_by_email, queries))

        assert results == [user] * len(queries)


class TestInMemorySessionStore(SessionStoreContract):
    @pytest.fixture
    def session_store(self) -> InMemorySessionStore:
        return InMemorySessionStore()

    @pytest.fixture
    def session_store_factory(self) -> Callable[[int], InMemorySessionStore]:
        def factory(max_sessions: int) -> InMemorySessionStore:
            return InMemorySessionStore(max_sessions=max_sessions)

        return factory

    def test_default_capacity_is_ten_thousand_sessions(self) -> None:
        store = InMemorySessionStore()
        for index in range(MAX_SESSIONS):
            store.create(_session(f"token-{index}", NOW + timedelta(seconds=index)))

        store.create(_session("overflow", NOW + timedelta(seconds=MAX_SESSIONS + 1)))

        assert len(store.snapshot()) == MAX_SESSIONS
        assert store.get("token-0") is None
        assert store.get("overflow") is not None

    def test_a_non_positive_capacity_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="max_sessions must be at least 1"):
            InMemorySessionStore(max_sessions=0)

    def test_recreating_a_token_replaces_the_stored_session(self) -> None:
        store = InMemorySessionStore(max_sessions=1)
        store.create(_session("token-hash", NOW))

        updated = _session("token-hash", NOW + timedelta(seconds=1))
        store.create(updated)

        assert store.get("token-hash") == updated

    def test_concurrent_creates_respect_the_capacity(self) -> None:
        store = InMemorySessionStore(max_sessions=50)

        def create(index: int) -> None:
            store.create(_session(f"token-{index}", NOW + timedelta(seconds=index)))

        with ThreadPoolExecutor(max_workers=16) as executor:
            list(executor.map(create, range(500)))

        assert len(store.snapshot()) <= 50

    def test_touch_cannot_resurrect_a_concurrently_deleted_session(self) -> None:
        store = InMemorySessionStore()
        store.create(_session())
        barrier = Barrier(2)

        def delete() -> None:
            barrier.wait()
            store.delete("token-hash")

        def touch() -> None:
            barrier.wait()
            store.touch("token-hash", NOW + timedelta(minutes=1))

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(delete), executor.submit(touch)]
            for future in futures:
                future.result()

        assert store.get("token-hash") is None

    def test_snapshot_returns_a_copy(self) -> None:
        store = InMemorySessionStore()
        store.create(_session())

        snapshot = store.snapshot()
        snapshot.clear()

        assert store.get("token-hash") is not None
