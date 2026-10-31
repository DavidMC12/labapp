"""Authentication service: login, session authentication and logout."""

from __future__ import annotations

import hashlib
import secrets
import threading
from collections.abc import Callable
from datetime import timedelta

from app.errors import ApiError
from app.infra.clock import Clock
from app.modules.auth.models import Session, User
from app.modules.auth.ports import SessionStore, UserRepository
from app.security.passwords import verify_password

SESSION_IDLE_TIMEOUT = timedelta(hours=8)
SESSION_PURGE_GRACE = timedelta(hours=24)
SESSION_PURGE_AGE = SESSION_IDLE_TIMEOUT + SESSION_PURGE_GRACE

INVALID_CREDENTIALS_MESSAGE = "Email o contraseña incorrectos."
UNAUTHENTICATED_MESSAGE = "Inicia sesión para continuar."
SESSION_EXPIRED_MESSAGE = "Tu sesión expiró. Inicia sesión de nuevo."


class AuthService:
    """Credential checks and server-side sessions over the storage ports."""

    def __init__(
        self,
        users: UserRepository,
        sessions: SessionStore,
        clock: Clock,
        *,
        dummy_hash: str,
        verify: Callable[[str, str], bool] = verify_password,
        max_concurrent_hashes: int = 2,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._clock = clock
        self._dummy_hash = dummy_hash
        self._verify = verify
        self._hash_slots = threading.BoundedSemaphore(max_concurrent_hashes)

    def _verify_password(self, password_hash: str, password: str) -> bool:
        with self._hash_slots:
            return self._verify(password_hash, password)

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def login(
        self,
        email: str,
        password: str,
        presented_token: str | None = None,
    ) -> tuple[User, str]:
        """Verify credentials, rotate the presented session and create a new one."""
        user = self._users.get_by_email(email.strip().lower())

        if user is None:
            self._verify_password(self._dummy_hash, password)
            raise ApiError(401, "INVALID_CREDENTIALS", INVALID_CREDENTIALS_MESSAGE)

        if not self._verify_password(user.password_hash, password):
            raise ApiError(401, "INVALID_CREDENTIALS", INVALID_CREDENTIALS_MESSAGE)

        now = self._clock.now()
        if presented_token:
            self._sessions.delete(self._hash_token(presented_token))

        self._sessions.purge_older_than(now - SESSION_PURGE_AGE)

        token = secrets.token_urlsafe(32)
        self._sessions.create(
            Session(
                token_hash=self._hash_token(token),
                user_id=user.id,
                created_at=now,
                last_seen_at=now,
            )
        )
        return user, token
