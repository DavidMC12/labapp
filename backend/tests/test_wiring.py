"""The database setting chooses the adapters without opening a connection."""

from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from app.config import Settings
from app.main import create_app
from app.modules.auth.adapters.memory import InMemorySessionStore, InMemoryUserRepository
from app.modules.auth.adapters.postgres import PostgresSessionStore, PostgresUserRepository
from app.modules.customers.adapters.memory import InMemoryCustomerRepository
from app.modules.customers.adapters.postgres import PostgresCustomerRepository

DATABASE_URL = "postgresql+psycopg://user:password@host/db"


def test_database_url_selects_the_postgres_adapters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("the application opened a connection")

    monkeypatch.setattr(psycopg, "connect", unexpected_connect)

    app = create_app(Settings(session_secret="test-secret", database_url=DATABASE_URL))

    assert isinstance(app.state.engine, Engine)
    assert isinstance(app.state.container.users, PostgresUserRepository)
    assert isinstance(app.state.container.sessions, PostgresSessionStore)
    assert isinstance(app.state.customer_repository, PostgresCustomerRepository)

    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_without_database_url_the_in_memory_adapters_stay() -> None:
    app = create_app(Settings(session_secret="test-secret"))

    assert app.state.engine is None
    assert isinstance(app.state.container.users, InMemoryUserRepository)
    assert isinstance(app.state.container.sessions, InMemorySessionStore)
    assert isinstance(app.state.customer_repository, InMemoryCustomerRepository)

    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
