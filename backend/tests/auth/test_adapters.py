"""Tests for the in-memory authentication adapters."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

from app.domain.permissions import Role
from app.modules.auth.adapters.memory import (
    MAX_SESSIONS,
    InMemorySessionStore,
    InMemoryUserRepository,
)
from app.modules.auth.models import Session, User

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


def test_email_lookup_is_case_insensitive() -> None:
    user = _user()
    repository = InMemoryUserRepository([user])

    assert repository.get_by_email("admin@labapp.test") == user
    assert repository.get_by_email("ADMIN@LABAPP.TEST") == user
    assert repository.get_by_email("  Admin@LabApp.Test  ") == user


def test_unknown_email_returns_none() -> None:
    repository = InMemoryUserRepository([_user()])

    assert repository.get_by_email("nobody@labapp.test") is None


def test_id_lookup() -> None:
    user = _user()
    repository = InMemoryUserRepository([user])

    assert repository.get_by_id(1) == user
    assert repository.get_by_id(99) is None


def test_concurrent_lookups_are_safe() -> None:
    user = _user()
    repository = InMemoryUserRepository([user])
    queries = ["ADMIN@LABAPP.TEST", "admin@labapp.test", "Admin@LabApp.Test"] * 50

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(repository.get_by_email, queries))

    assert results == [user] * len(queries)


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


def test_create_and_get_a_session() -> None:
    store = InMemorySessionStore()
    session = _session()

    store.create(session)

    assert store.get("token-hash") == session
    assert store.snapshot() == [session]


def test_touch_updates_an_existing_session() -> None:
    store = InMemorySessionStore()
    store.create(_session())
    later = NOW + timedelta(minutes=5)

    store.touch("token-hash", later)

    session = store.get("token-hash")
    assert session is not None
    assert session.last_seen_at == later


def test_touch_on_an_unknown_key_is_a_noop() -> None:
    store = InMemorySessionStore()

    store.touch("missing", NOW)

    assert store.get("missing") is None
    assert store.snapshot() == []


def test_delete_removes_a_session_and_ignores_unknown_keys() -> None:
    store = InMemorySessionStore()
    store.create(_session())

    store.delete("missing")
    assert store.get("token-hash") is not None

    store.delete("token-hash")
    assert store.get("token-hash") is None
    store.delete("token-hash")


def test_touch_does_not_resurrect_a_deleted_session() -> None:
    store = InMemorySessionStore()
    store.create(_session())
    store.delete("token-hash")

    store.touch("token-hash", NOW + timedelta(minutes=1))

    assert store.get("token-hash") is None
    assert store.snapshot() == []


def test_purge_uses_a_strict_cutoff() -> None:
    store = InMemorySessionStore()
    store.create(_session("old", NOW - timedelta(seconds=1)))
    store.create(_session("boundary", NOW))
    store.create(_session("recent", NOW + timedelta(seconds=1)))

    removed = store.purge_older_than(NOW)

    assert removed == 1
    assert store.get("old") is None
    assert store.get("boundary") is not None
    assert store.get("recent") is not None


def test_capacity_evicts_the_oldest_sessions() -> None:
    store = InMemorySessionStore(max_sessions=3)
    for index in range(5):
        store.create(_session(f"token-{index}", NOW + timedelta(seconds=index)))

    snapshot = store.snapshot()

    assert len(snapshot) == 3
    assert {session.token_hash for session in snapshot} == {
        "token-2",
        "token-3",
        "token-4",
    }


def test_default_capacity_is_ten_thousand_sessions() -> None:
    store = InMemorySessionStore()
    for index in range(MAX_SESSIONS):
        store.create(_session(f"token-{index}", NOW + timedelta(seconds=index)))

    store.create(_session("overflow", NOW + timedelta(seconds=MAX_SESSIONS + 1)))

    assert len(store.snapshot()) == MAX_SESSIONS
    assert store.get("token-0") is None
    assert store.get("overflow") is not None


def test_concurrent_creates_respect_the_capacity() -> None:
    store = InMemorySessionStore(max_sessions=50)

    def create(index: int) -> None:
        store.create(_session(f"token-{index}", NOW + timedelta(seconds=index)))

    with ThreadPoolExecutor(max_workers=16) as executor:
        list(executor.map(create, range(500)))

    assert len(store.snapshot()) <= 50


def test_touch_cannot_resurrect_a_concurrently_deleted_session() -> None:
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


def test_snapshot_returns_a_copy() -> None:
    store = InMemorySessionStore()
    store.create(_session())

    snapshot = store.snapshot()
    snapshot.clear()

    assert store.get("token-hash") is not None
