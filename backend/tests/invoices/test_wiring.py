"""Tests for the invoice wiring."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

DATABASE_URL = "postgresql+psycopg://user:password@host/db"


def test_the_memory_application_wires_the_invoice_module() -> None:
    app = create_app(Settings(session_secret="test-secret", test_mode=False))

    assert app.state.invoices is not None
    assert app.state.invoice_store is not None
    assert app.state.payment_gateway is not None


def test_a_database_application_builds_without_the_invoice_module() -> None:
    app = create_app(
        Settings(
            session_secret="test-secret",
            test_mode=False,
            database_url=DATABASE_URL,
        )
    )
    client = TestClient(app)

    assert client.get("/api/health").status_code == 200
    assert client.get("/api/invoices").status_code == 404
    assert not hasattr(app.state, "invoices")
