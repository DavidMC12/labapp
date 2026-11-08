"""Shared fixtures for the customer tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.infra.clock import OffsetClock
from app.main import create_app
from app.modules.auth.seed import DEMO_PASSWORD
from app.modules.customers.seed import seed_customers
from tests.infra.helpers import FixedClock

CLIENTS = {
    "admin": "admin@labapp.test",
    "sales": "sales@labapp.test",
    "finance": "finance@labapp.test",
    "readonly": "readonly@labapp.test",
}


@pytest.fixture(scope="module")
def clock() -> OffsetClock:
    return OffsetClock(FixedClock(datetime(2026, 11, 5, 23, 0, tzinfo=UTC)))


@pytest.fixture(scope="module")
def app(clock: OffsetClock) -> FastAPI:
    return create_app(
        Settings(
            session_secret="test-secret",
            test_mode=False,
            app_origin="http://localhost:3000",
        ),
        clock=clock,
    )


@pytest.fixture(scope="module")
def clients(app: FastAPI) -> dict[str, TestClient]:
    result: dict[str, TestClient] = {}
    for role, email in CLIENTS.items():
        client = TestClient(app)
        response = client.post(
            "/api/auth/login",
            json={"email": email, "password": DEMO_PASSWORD},
        )
        assert response.status_code == 200
        result[role] = client
    return result


@pytest.fixture(autouse=True)
def reset_customers(app: FastAPI) -> None:
    app.state.customer_repository.replace_all(seed_customers())


@pytest.fixture(autouse=True)
def reset_limiters(app: FastAPI) -> None:
    app.state.container.reset_limiters()
