"""Shared fixtures for the invoice tests."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.domain.money import quantize_money
from app.infra.clock import OffsetClock, SystemClock
from app.main import create_app
from app.modules.auth.seed import DEMO_PASSWORD
from app.modules.customers.seed import seed_customers
from app.modules.invoices.seed import seed_invoices, seed_payments
from app.modules.orders.seed import seed_orders, seed_products

CLIENTS = {
    "admin": "admin@labapp.test",
    "sales": "sales@labapp.test",
    "finance": "finance@labapp.test",
    "readonly": "readonly@labapp.test",
}


@pytest.fixture(scope="module")
def app() -> FastAPI:
    return create_app(
        Settings(
            session_secret="test-secret",
            test_mode=False,
            app_origin="http://localhost:3000",
        ),
        clock=OffsetClock(SystemClock()),
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
def reset_invoices(app: FastAPI) -> None:
    app.state.customer_repository.replace_all(seed_customers())
    app.state.order_store.replace_all(
        seed_products(),
        seed_orders(),
        quantize_money(app.state.settings.default_tax_rate),
    )
    app.state.invoice_store.replace_all(seed_invoices(), seed_payments())


@pytest.fixture(autouse=True)
def reset_limiters(app: FastAPI) -> None:
    app.state.container.reset_limiters()
