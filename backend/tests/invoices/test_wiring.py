"""Tests for the invoice wiring."""

from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.modules.invoices.adapters.memory import InMemoryInvoiceStore
from app.modules.invoices.adapters.postgres import PostgresInvoiceStore

DATABASE_URL = "postgresql+psycopg://user:password@host/db"


def test_the_memory_application_wires_the_invoice_module() -> None:
    app = create_app(Settings(session_secret="test-secret", test_mode=False))

    assert isinstance(app.state.invoice_store, InMemoryInvoiceStore)
    assert app.state.invoices is not None
    assert app.state.payment_gateway is not None


def test_a_database_application_wires_the_invoice_module_without_connecting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("the application opened a connection")

    monkeypatch.setattr(psycopg, "connect", unexpected_connect)

    app = create_app(
        Settings(
            session_secret="test-secret",
            test_mode=False,
            database_url=DATABASE_URL,
        )
    )

    assert isinstance(app.state.invoice_store, PostgresInvoiceStore)
    assert app.state.invoices is not None
    assert app.state.payment_gateway is not None
    assert TestClient(app).get("/api/health").status_code == 200
