"""Reusable behavioral tests for UserRepository adapters."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from app.domain.permissions import Role
from app.modules.auth.models import User

NOW = datetime(2026, 1, 1, 8, 0, tzinfo=UTC)


def user(
    id: int = 1,
    name: str = "Admin Demo",
    email: str = "admin@labapp.test",
    role: Role = Role.ADMIN,
) -> User:
    """Build a user for the contract tests."""
    return User(
        id=id,
        name=name,
        email=email,
        role=role,
        password_hash="hash",
        created_at=NOW,
    )


class UserRepositoryContract:
    """The behavior every UserRepository adapter must share.

    A concrete test class provides ``user_repository``, a fresh repository with
    the user returned by ``user()``.
    """

    @pytest.fixture
    def user_repository(self) -> Any:
        raise NotImplementedError

    def test_lookup_by_normalized_email(self, user_repository: Any) -> None:
        assert user_repository.get_by_email("admin@labapp.test") == user()

    def test_unknown_email_returns_none(self, user_repository: Any) -> None:
        assert user_repository.get_by_email("nobody@labapp.test") is None

    def test_id_lookup(self, user_repository: Any) -> None:
        assert user_repository.get_by_id(1) == user()
        assert user_repository.get_by_id(99) is None
