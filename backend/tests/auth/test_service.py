"""Tests for the authentication service."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from hashlib import sha256
from threading import Event, Lock

import pytest

from app.errors import ApiError
from app.infra.clock import OffsetClock
from app.modules.auth.adapters.memory import InMemorySessionStore, InMemoryUserRepository
from app.modules.auth.models import Session
from app.modules.auth.seed import DEMO_PASSWORD
from app.modules.auth.service import (
    INVALID_CREDENTIALS_MESSAGE,
    SESSION_PURGE_AGE,
    AuthService,
)
from tests.auth.helpers import RecordingVerifier


def _hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def test_login_returns_the_user_and_stores_only_the_token_hash(
    service: AuthService,
    sessions: InMemorySessionStore,
    clock: OffsetClock,
) -> None:
    before = clock.now()

    user, token = service.login("admin@labapp.test", DEMO_PASSWORD)

    assert user.id == 1
    snapshot = sessions.snapshot()
    assert len(snapshot) == 1
    session = snapshot[0]
    assert session.token_hash == _hash_token(token)
    assert session.token_hash != token
    assert session.user_id == 1
    assert session.created_at == before
    assert session.last_seen_at == before


def test_login_trims_and_lowercases_the_email(service: AuthService) -> None:
    user, _ = service.login("  ADMIN@LABAPP.TEST  ", DEMO_PASSWORD)

    assert user.email == "admin@labapp.test"


def test_wrong_password_raises_invalid_credentials(
    service: AuthService,
    sessions: InMemorySessionStore,
    users: InMemoryUserRepository,
    verifier: RecordingVerifier,
) -> None:
    with pytest.raises(ApiError) as error:
        service.login("admin@labapp.test", "wrong-password")

    assert error.value.status == 401
    assert error.value.code == "INVALID_CREDENTIALS"
    assert error.value.detail == INVALID_CREDENTIALS_MESSAGE
    assert verifier.calls == [(users.get_by_id(1).password_hash, "wrong-password")]
    assert sessions.snapshot() == []


def test_unknown_email_verifies_against_the_dummy_hash(
    service: AuthService,
    sessions: InMemorySessionStore,
    verifier: RecordingVerifier,
    dummy_hash_value: str,
) -> None:
    with pytest.raises(ApiError):
        service.login("nobody@labapp.test", "wrong-password")

    assert verifier.calls == [(dummy_hash_value, "wrong-password")]
    assert sessions.snapshot() == []


def test_unknown_email_with_the_demo_password_still_fails(
    service: AuthService,
    sessions: InMemorySessionStore,
    verifier: RecordingVerifier,
    dummy_hash_value: str,
) -> None:
    with pytest.raises(ApiError) as error:
        service.login("nobody@labapp.test", DEMO_PASSWORD)

    assert error.value.code == "INVALID_CREDENTIALS"
    assert verifier.calls == [(dummy_hash_value, DEMO_PASSWORD)]
    assert sessions.snapshot() == []


def test_unknown_email_and_wrong_password_share_the_same_error(
    service: AuthService,
) -> None:
    with pytest.raises(ApiError) as unknown:
        service.login("nobody@labapp.test", "wrong-password")
    with pytest.raises(ApiError) as wrong:
        service.login("admin@labapp.test", "wrong-password")

    assert unknown.value.status == wrong.value.status
    assert unknown.value.code == wrong.value.code
    assert unknown.value.detail == wrong.value.detail


def test_login_revokes_the_presented_session(
    service: AuthService,
    sessions: InMemorySessionStore,
) -> None:
    _, first_token = service.login("admin@labapp.test", DEMO_PASSWORD)

    _, second_token = service.login(
        "admin@labapp.test",
        DEMO_PASSWORD,
        presented_token=first_token,
    )

    assert sessions.get(_hash_token(first_token)) is None
    assert sessions.get(_hash_token(second_token)) is not None


def test_login_ignores_an_unknown_presented_token(service: AuthService) -> None:
    user, token = service.login(
        "admin@labapp.test",
        DEMO_PASSWORD,
        presented_token="unknown-token",
    )

    assert user.id == 1
    assert token


def test_login_creates_a_fresh_token_each_time(service: AuthService) -> None:
    _, first = service.login("admin@labapp.test", DEMO_PASSWORD)
    _, second = service.login("admin@labapp.test", DEMO_PASSWORD)

    assert first != second


def test_login_purges_sessions_older_than_32_hours(
    service: AuthService,
    sessions: InMemorySessionStore,
    clock: OffsetClock,
) -> None:
    now = clock.now()
    old = now - SESSION_PURGE_AGE - timedelta(seconds=1)
    boundary = now - SESSION_PURGE_AGE
    recent = now - timedelta(hours=1)
    sessions.create(Session("old", 1, old, old))
    sessions.create(Session("boundary", 1, boundary, boundary))
    sessions.create(Session("recent", 1, recent, recent))

    service.login("admin@labapp.test", DEMO_PASSWORD)

    assert sessions.get("old") is None
    assert sessions.get("boundary") is not None
    assert sessions.get("recent") is not None


class BlockingVerifier:
    """A verifier that blocks until two calls overlap, to measure concurrency."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.active = 0
        self.max_active = 0
        self.two_active = Event()
        self.release = Event()

    def __call__(self, password_hash: str, password: str) -> bool:
        with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            if self.active == 2:
                self.two_active.set()
        self.release.wait(timeout=5)
        with self._lock:
            self.active -= 1
        return password == DEMO_PASSWORD


def test_verifications_are_limited_to_the_semaphore_size(
    users: InMemoryUserRepository,
    sessions: InMemorySessionStore,
    clock: OffsetClock,
) -> None:
    verifier = BlockingVerifier()
    service = AuthService(
        users,
        sessions,
        clock,
        dummy_hash="dummy-hash",
        verify=verifier,
        max_concurrent_hashes=2,
    )

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(service.login, "admin@labapp.test", DEMO_PASSWORD) for _ in range(4)
        ]
        assert verifier.two_active.wait(timeout=5) is True
        verifier.release.set()
        results = [future.result(timeout=5) for future in futures]

    assert verifier.max_active == 2
    assert all(user.id == 1 for user, _ in results)
