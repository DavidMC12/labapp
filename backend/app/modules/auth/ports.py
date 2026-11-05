"""Storage ports for the authentication module."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.modules.auth.models import Session, User


class UserRepository(Protocol):
    """Read access to user accounts."""

    def get_by_email(self, email: str) -> User | None:
        """Return the user with that email, or ``None``.

        The caller passes an already normalized email (trimmed and lowercased).
        """
        ...

    def get_by_id(self, id: int) -> User | None:
        """Return the user with that id, or ``None``."""
        ...


class SessionStore(Protocol):
    """Storage for server-side sessions."""

    def create(self, session: Session) -> None:
        """Store a session.

        The store keeps at most its configured cap. When creating would exceed it,
        the sessions with the oldest ``last_seen_at`` are removed first. A
        PostgreSQL adapter must count and evict in one transaction.
        """
        ...

    def get(self, token_hash: str) -> Session | None:
        """Return the session with that token digest, or ``None``."""
        ...

    def touch(self, token_hash: str, when: datetime) -> None:
        """Record activity on a known session.

        An unknown key is a no-op: ``touch`` never creates a session and never
        brings back one that was deleted. It is monotonic: it never moves
        ``last_seen_at`` backwards, so an older ``when`` leaves the stored value
        unchanged.
        """
        ...

    def delete(self, token_hash: str) -> None:
        """Delete a session; an unknown key is a no-op."""
        ...

    def purge_older_than(self, cutoff: datetime) -> int:
        """Delete the sessions whose ``last_seen_at`` is strictly before the cutoff.

        Return how many sessions were removed.
        """
        ...
