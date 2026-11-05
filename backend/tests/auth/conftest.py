"""Shared fixtures for the authentication tests."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.infra.clock import OffsetClock
from app.main import create_app
from app.modules.auth.adapters.memory import InMemorySessionStore, InMemoryUserRepository
from app.modules.auth.seed import demo_password_hash, seed_users
from app.modules.auth.service import AuthService
from tests.auth.helpers import DUMMY_HASH, NOW, FixedClock, RecordingVerifier


@pytest.fixture
def fixed_clock() -> FixedClock:
    return FixedClock(NOW)


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


@pytest.fixture
def make_app() -> Callable[..., FastAPI]:
    def factory(
        *,
        app_origin: str = "http://localhost:3000",
        now: datetime = NOW,
    ) -> FastAPI:
        return create_app(
            Settings(
                session_secret="test-secret",
                test_mode=False,
                app_origin=app_origin,
            ),
            clock=OffsetClock(FixedClock(now)),
        )

    return factory


@pytest.fixture
def app(make_app: Callable[..., FastAPI]) -> FastAPI:
    return make_app()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)
