"""Authentication service: login, session authentication and logout."""

from __future__ import annotations

import hashlib
import secrets
import threading
from collections.abc import Callable, Iterable
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
SERVICE_BUSY_MESSAGE = "El servicio está ocupado. Inténtalo de nuevo en unos segundos."


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
        max_waiting_hashes: int = 2,
        hash_wait_seconds: float = 2.0,
    ) -> None:
        if max_concurrent_hashes < 1:
            raise ValueError("max_concurrent_hashes must be at least 1")
        if max_waiting_hashes < 0:
            raise ValueError("max_waiting_hashes must be at least 0")
        self._users = users
        self._sessions = sessions
        self._clock = clock
        self._dummy_hash = dummy_hash
        self._verify = verify
        self._hash_wait_seconds = hash_wait_seconds
        self._hash_slots = threading.BoundedSemaphore(max_concurrent_hashes)
        self._max_hash_load = max_concurrent_hashes + max_waiting_hashes
        self._hash_load = 0
        self._hash_load_lock = threading.Lock()

    def _verify_password(self, password_hash: str, password: str) -> bool:
        with self._hash_load_lock:
            if self._hash_load >= self._max_hash_load:
                raise ApiError(503, "SERVICE_BUSY", SERVICE_BUSY_MESSAGE)
            self._hash_load += 1
        try:
            if not self._hash_slots.acquire(timeout=self._hash_wait_seconds):
                raise ApiError(503, "SERVICE_BUSY", SERVICE_BUSY_MESSAGE)
            try:
                return self._verify(password_hash, password)
            finally:
                self._hash_slots.release()
        finally:
            with self._hash_load_lock:
                self._hash_load -= 1

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def login(
        self,
        email: str,
        password: str,
        presented_token: str | None = None,
        *,
        presented_tokens: Iterable[str] = (),
    ) -> tuple[User, str]:
        """Verify credentials, rotate the presented session and create a new one."""
        user = self._users.get_by_email(email.strip().lower())

        if user is None:
            self._verify_password(self._dummy_hash, password)
            raise ApiError(401, "INVALID_CREDENTIALS", INVALID_CREDENTIALS_MESSAGE)

        if not self._verify_password(user.password_hash, password):
            raise ApiError(401, "INVALID_CREDENTIALS", INVALID_CREDENTIALS_MESSAGE)

        now = self._clock.now()
        tokens = set(presented_tokens)
        if presented_token:
            tokens.add(presented_token)
        for token in tokens:
            if token:
                self._sessions.delete(self._hash_token(token))

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

    def authenticate(self, token: str | None) -> User:
        """Return the user for a live session, sliding its idle window."""
        if not token:
            raise ApiError(401, "UNAUTHENTICATED", UNAUTHENTICATED_MESSAGE)

        token_hash = self._hash_token(token)
        session = self._sessions.get(token_hash)
        if session is None:
            raise ApiError(401, "UNAUTHENTICATED", UNAUTHENTICATED_MESSAGE)

        now = self._clock.now()
        if now - session.last_seen_at >= SESSION_IDLE_TIMEOUT:
            raise ApiError(401, "SESSION_EXPIRED", SESSION_EXPIRED_MESSAGE)

        user = self._users.get_by_id(session.user_id)
        if user is None:
            self._sessions.delete(token_hash)
            raise ApiError(401, "UNAUTHENTICATED", UNAUTHENTICATED_MESSAGE)

        self._sessions.touch(token_hash, now)
        return user

    def logout(self, token: str | None) -> None:
        """Delete the session if present; missing tokens are ignored."""
        if token:
            self._sessions.delete(self._hash_token(token))
