"""Shared fixtures for the authentication tests."""

from __future__ import annotations

import pytest

from app.infra.clock import OffsetClock
from app.modules.auth.adapters.memory import InMemorySessionStore, InMemoryUserRepository
from app.modules.auth.seed import demo_password_hash, seed_users
from app.modules.auth.service import AuthService
from tests.auth.helpers import DUMMY_HASH, FixedClock, RecordingVerifier


@pytest.fixture
def fixed_clock() -> FixedClock:
    return FixedClock()


@pytest.fixture
def clock(fixed_clock: FixedClock) -> OffsetClock:
    return OffsetClock(fixed_clock)


@pytest.fixture
def users() -> InMemoryUserRepository:
    return InMemoryUserRepository(seed_users(demo_password_hash()))


@pytest.fixture
def sessions() -> InMemorySessionStore:
    return InMemorySessionStore()


@pytest.fixture
def verifier() -> RecordingVerifier:
    return RecordingVerifier()


@pytest.fixture
def dummy_hash_value() -> str:
    return DUMMY_HASH


@pytest.fixture
def service(
    users: InMemoryUserRepository,
    sessions: InMemorySessionStore,
    clock: OffsetClock,
    verifier: RecordingVerifier,
) -> AuthService:
    return AuthService(
        users,
        sessions,
        clock,
        dummy_hash=DUMMY_HASH,
        verify=verifier,
    )
