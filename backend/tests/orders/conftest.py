"""Shared fixtures for the order tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.domain.money import quantize_money
from app.infra.clock import OffsetClock
from app.main import create_app
from app.modules.auth.seed import DEMO_PASSWORD
from app.modules.customers.seed import seed_customers
from app.modules.orders.seed import seed_orders, seed_products
from tests.infra.helpers import FixedClock

CLIENTS = {
    "admin": "admin@labapp.test",
    "sales": "sales@labapp.test",
    "finance": "finance@labapp.test",
    "readonly": "readonly@labapp.test",
}


@pytest.fixture(scope="module")
def app_clock() -> OffsetClock:
    return OffsetClock(FixedClock(datetime(2026, 11, 5, 23, 0, tzinfo=UTC)))


@pytest.fixture(scope="module")
def app(app_clock: OffsetClock) -> FastAPI:
    return create_app(
        Settings(
            session_secret="test-secret",
            test_mode=False,
            app_origin="http://localhost:3000",
        ),
        clock=app_clock,
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
def reset_orders(app: FastAPI) -> None:
    app.state.customer_repository.replace_all(seed_customers())
    app.state.order_store.replace_all(
        seed_products(),
        seed_orders(),
        quantize_money(app.state.settings.default_tax_rate),
    )


@pytest.fixture
def draft_id(clients: dict[str, TestClient]) -> int:
    response = clients["sales"].post("/api/orders", json={"customer_id": 1})
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture(autouse=True)
def reset_limiters(app: FastAPI) -> None:
    app.state.container.reset_limiters()
