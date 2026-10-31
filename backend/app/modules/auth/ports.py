"""Storage ports for the authentication module."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.modules.auth.models import Session, User


class UserRepository(Protocol):
    """Read access to user accounts."""

    def get_by_email(self, email: str) -> User | None: ...

    def get_by_id(self, id: int) -> User | None: ...


class SessionStore(Protocol):
    """Storage for server-side sessions."""

    def create(self, session: Session) -> None: ...

    def get(self, token_hash: str) -> Session | None: ...

    def touch(self, token_hash: str, when: datetime) -> None: ...

    def delete(self, token_hash: str) -> None: ...

    def purge_older_than(self, cutoff: datetime) -> int: ...
