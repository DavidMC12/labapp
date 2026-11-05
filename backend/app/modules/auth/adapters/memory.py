"""In-memory adapters for the authentication ports."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from datetime import datetime
from threading import Lock

from app.modules.auth.models import Session, User

MAX_SESSIONS = 10_000


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


class InMemorySessionStore:
    """A thread-safe session store bounded to a maximum number of sessions."""

    def __init__(self, max_sessions: int = MAX_SESSIONS) -> None:
        if max_sessions < 1:
            raise ValueError("max_sessions must be at least 1")
        self._max_sessions = max_sessions
        self._sessions: dict[str, Session] = {}
        self._lock = Lock()

    def create(self, session: Session) -> None:
        with self._lock:
            if session.token_hash not in self._sessions:
                while len(self._sessions) >= self._max_sessions:
                    oldest = min(
                        self._sessions,
                        key=lambda token_hash: self._sessions[token_hash].last_seen_at,
                    )
                    del self._sessions[oldest]
            self._sessions[session.token_hash] = session

    def get(self, token_hash: str) -> Session | None:
        with self._lock:
            return self._sessions.get(token_hash)

    def touch(self, token_hash: str, when: datetime) -> None:
        with self._lock:
            session = self._sessions.get(token_hash)
            if session is not None and when > session.last_seen_at:
                self._sessions[token_hash] = replace(session, last_seen_at=when)

    def delete(self, token_hash: str) -> None:
        with self._lock:
            self._sessions.pop(token_hash, None)

    def purge_older_than(self, cutoff: datetime) -> int:
        with self._lock:
            expired = [
                token_hash
                for token_hash, session in self._sessions.items()
                if session.last_seen_at < cutoff
            ]
            for token_hash in expired:
                del self._sessions[token_hash]
            return len(expired)

    def snapshot(self) -> list[Session]:
        with self._lock:
            return list(self._sessions.values())
