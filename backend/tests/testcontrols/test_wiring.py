"""The controls stores chosen by the settings, without opening a connection."""

from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.infra.clock import ControlledClock, OffsetClock
from app.main import create_app
from app.modules.invoices.adapters.memory import InMemoryInvoiceStore
from app.modules.invoices.adapters.postgres import PostgresInvoiceStore
from app.modules.invoices.gateway import FakeGateway
from app.modules.testcontrols.memory import (
    InMemoryClockOffsetStore,
    InMemoryFaultStore,
)
from app.modules.testcontrols.postgres import (
    PostgresClockOffsetStore,
    PostgresFaultStore,
)

DATABASE_URL = "postgresql+psycopg://user:password@host/db"


def _no_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected(*args: object, **kwargs: object) -> None:
        raise AssertionError("the application opened a connection")

    monkeypatch.setattr(psycopg, "connect", unexpected)


def test_the_memory_application_uses_the_in_memory_control_stores() -> None:
    app = create_app(Settings(session_secret="test-secret", test_mode=False))

    assert isinstance(app.state.clock_store, InMemoryClockOffsetStore)
    assert isinstance(app.state.fault_store, InMemoryFaultStore)
    assert isinstance(app.state.container.clock, OffsetClock)
    assert isinstance(app.state.payment_gateway, FakeGateway)
    assert isinstance(app.state.invoice_store, InMemoryInvoiceStore)


def test_the_database_application_uses_the_postgres_control_stores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _no_connection(monkeypatch)

    app = create_app(
        Settings(
            session_secret="test-secret",
            test_mode=False,
            database_url=DATABASE_URL,
        )
    )

    assert isinstance(app.state.clock_store, PostgresClockOffsetStore)
    assert isinstance(app.state.fault_store, PostgresFaultStore)
    assert isinstance(app.state.container.clock, ControlledClock)
    assert app.state.container.clock.enabled is False
    assert isinstance(app.state.payment_gateway, FakeGateway)
    assert isinstance(app.state.invoice_store, PostgresInvoiceStore)
    assert TestClient(app).get("/api/health").status_code == 200


def test_test_mode_enables_the_database_controlled_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _no_connection(monkeypatch)

    app = create_app(
        Settings(
            session_secret="test-secret",
            test_mode=True,
            database_url=DATABASE_URL,
        )
    )

    assert isinstance(app.state.container.clock, ControlledClock)
    assert app.state.container.clock.enabled is True
    assert TestClient(app).get("/api/health").status_code == 200
