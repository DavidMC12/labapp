"""Tests for the in-memory authentication adapters."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from app.domain.permissions import Role
from app.modules.auth.adapters.memory import InMemoryUserRepository
from app.modules.auth.models import User

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
