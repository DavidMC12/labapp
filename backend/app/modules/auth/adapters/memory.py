"""In-memory adapters for the authentication ports."""

from __future__ import annotations

from collections.abc import Iterable
from threading import Lock

from app.modules.auth.models import User


class InMemoryUserRepository:
    """A thread-safe user repository backed by dictionaries."""

    def __init__(self, users: Iterable[User] = ()) -> None:
        self._lock = Lock()
        self._by_id: dict[int, User] = {}
        self._by_email: dict[str, User] = {}
        for user in users:
            self._by_id[user.id] = user
            self._by_email[user.email.strip().lower()] = user

    def get_by_email(self, email: str) -> User | None:
        with self._lock:
            return self._by_email.get(email.strip().lower())

    def get_by_id(self, id: int) -> User | None:
        with self._lock:
            return self._by_id.get(id)
