"""A reset restores every module and keeps the sessions."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError, IntegrityError

import app.modules.testcontrols.reset as reset_module
from app.domain.orders import OrderAction, OrderStatus
from app.modules.testcontrols.models import NewRule
from app.modules.testcontrols.reset import MemoryResetter, PostgresResetter

from .helpers import login

NOW = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)


def _fill_general_limiter(app: FastAPI) -> None:
    limiter = app.state.container.limiters.general
    for _ in range(120):
        limiter.hit("test-client")
    assert limiter.hit("test-client").allowed is False


def test_reset_restores_every_module_and_keeps_the_session(
    controls_app: FastAPI,
    controls_client: TestClient,
) -> None:
    login(controls_client)
    controls_app.state.customer_repository.update(1, {"name": "Changed"}, None, NOW)
    controls_app.state.order_store.transition(1, OrderAction.CONFIRM, None, NOW)
    issued = controls_app.state.invoices.issue(2, None)
    controls_app.state.order_store.set_tax_rate(Decimal("20"))
    controls_app.state.clock_store.set(3600)
    controls_app.state.fault_store.add(NewRule(target="gateway", remaining=1))
    _fill_general_limiter(controls_app)

    assert controls_app.state.customer_repository.get(1).name == "Changed"
    assert controls_app.state.order_store.get_order(1).status == OrderStatus.CONFIRMED
    assert controls_app.state.invoice_store.get_invoice(issued.id) is not None
    assert controls_app.state.order_store.get_product(1).stock == 118
    assert controls_app.state.order_store.get_tax_rate() == Decimal("20.00")

    response = controls_client.post("/__test__/reset")

    assert response.status_code == 200
    customer = controls_app.state.customer_repository.get(1)
    assert customer is not None
    assert customer.name == "Acme Industrial S.A."
    assert customer.version == 1
    order = controls_app.state.order_store.get_order(1)
    assert order is not None
    assert order.status == OrderStatus.DRAFT
    assert order.version == 1
    assert controls_app.state.invoice_store.get_invoice(issued.id) is None
    assert (
        controls_app.state.invoice_store.list_invoices(
            query=None,
            status=None,
            order_id=None,
            page=1,
            page_size=20,
        )[1]
        == 3
    )
    assert controls_app.state.order_store.get_product(1).stock == 120
    assert controls_app.state.order_store.get_tax_rate() == Decimal("10.00")
    assert controls_app.state.clock_store.get() == 0.0
    assert controls_app.state.fault_store.list() == []
    assert controls_app.state.container.limiters.general.hit("test-client").allowed is True

    session = controls_client.get("/api/auth/me")

    assert session.status_code == 200
    assert session.json()["email"] == "admin@labapp.test"


def test_a_foreign_key_error_answers_conflict(
    controls_app: FastAPI,
    controls_client: TestClient,
) -> None:
    def fail() -> None:
        raise IntegrityError("statement", {}, Exception("foreign key"))

    controls_app.state.resetter = SimpleNamespace(reset=fail)

    response = controls_client.post("/__test__/reset")

    assert response.status_code == 409
    assert response.json()["code"] == "RESET_CONFLICT"
    assert "Inténtalo de nuevo." in response.json()["detail"]


@pytest.mark.parametrize(
    ("error", "sqlstate"),
    [
        (
            IntegrityError(
                "statement",
                {},
                psycopg.errors.ForeignKeyViolation("foreign key secret"),
            ),
            "23503",
        ),
        (
            DBAPIError(
                "statement",
                {},
                psycopg.errors.DeadlockDetected("deadlock secret"),
            ),
            "40P01",
        ),
    ],
)
def test_a_lost_race_answers_conflict_and_logs_safely(
    controls_app: FastAPI,
    controls_client: TestClient,
    caplog: pytest.LogCaptureFixture,
    error: DBAPIError,
    sqlstate: str,
) -> None:
    def fail(_dataset: str | None = None) -> None:
        raise error

    controls_app.state.resetter = SimpleNamespace(reset=fail, seed=fail)

    with caplog.at_level(logging.WARNING):
        reset = controls_client.post("/__test__/reset")
        seeded = controls_client.post("/__test__/seed", json={"dataset": "default"})

    for response in (reset, seeded):
        assert response.status_code == 409
        assert response.json()["code"] == "RESET_CONFLICT"
    assert type(error).__name__ in caplog.text
    assert sqlstate in caplog.text
    assert "secret" not in caplog.text


def test_another_database_error_stays_a_500(
    controls_app: FastAPI,
    controls_client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    error = DBAPIError(
        "statement",
        {},
        psycopg.errors.UndefinedTable("relation secret does not exist"),
    )

    def fail(_dataset: str | None = None) -> None:
        raise error

    controls_app.state.resetter = SimpleNamespace(reset=fail, seed=fail)

    with caplog.at_level(logging.ERROR):
        response = controls_client.post("/__test__/reset")

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
    assert "42P01" in caplog.text
    assert "secret" not in caplog.text


def _memory_resetter(app: FastAPI, limiters: list[None] | None = None) -> MemoryResetter:
    return MemoryResetter(
        customers=app.state.customer_repository,
        orders=app.state.order_store,
        invoices=app.state.invoice_store,
        clock_store=app.state.clock_store,
        fault_store=app.state.fault_store,
        default_tax_rate=Decimal("10"),
        reset_limiters=None if limiters is None else lambda: limiters.append(None),
    )


def test_a_memory_reset_without_a_limiter_callable_still_restores(
    controls_app: FastAPI,
) -> None:
    controls_app.state.customer_repository.update(1, {"name": "Changed"}, None, NOW)
    controls_app.state.clock_store.set(3600)
    resetter = _memory_resetter(controls_app)

    resetter.reset()

    assert controls_app.state.customer_repository.get(1).name == "Acme Industrial S.A."
    assert controls_app.state.clock_store.get() == 0.0


def test_a_memory_seed_loads_the_default_or_the_empty_dataset(controls_app: FastAPI) -> None:
    resetter = _memory_resetter(controls_app)

    controls_app.state.customer_repository.update(1, {"name": "Changed"}, None, NOW)
    controls_app.state.clock_store.set(3600)
    resetter.seed("default")

    assert controls_app.state.customer_repository.get(1).name == "Acme Industrial S.A."

    resetter.seed("empty")

    assert controls_app.state.customer_repository.get(1) is None
    assert controls_app.state.clock_store.get() == 0.0
    assert controls_app.state.fault_store.list() == []


def test_a_memory_seed_with_an_unknown_dataset_is_rejected(controls_app: FastAPI) -> None:
    resetter = _memory_resetter(controls_app)

    with pytest.raises(ValueError, match="Unknown dataset: other"):
        resetter.seed("other")  # type: ignore[arg-type]


class FakeConnection:
    """Record the statements of the resetter without opening a connection."""

    def __init__(self, log: list[tuple[str, Any]]) -> None:
        self.log = log

    def execute(self, statement: object, parameters: object = None) -> None:
        self.log.append(("sql", str(statement)))


class FakeEngine:
    """Yield one recording connection per transaction."""

    def __init__(self, log: list[tuple[str, Any]]) -> None:
        self.log = log
        self.connection = FakeConnection(log)
        self.transactions = 0

    @contextmanager
    def begin(self) -> Iterator[FakeConnection]:
        self.transactions += 1
        yield self.connection


class FakeRepository:
    """Record a replace_all call and defer the sequence restarts it would run."""

    def __init__(self, name: str, log: list[tuple[str, Any]], restarts: int = 1) -> None:
        self.name = name
        self.log = log
        self.restarts = restarts

    def replace_all(
        self,
        *args: object,
        connection: object = None,
        defer_sequences: list[Any] | None = None,
    ) -> None:
        self.log.append((self.name, connection))
        if defer_sequences is None:
            return
        for _ in range(self.restarts):
            defer_sequences.append(
                lambda conn, name=self.name: self.log.append((f"restart-{name}", conn))
            )


def _postgres_resetter(
    monkeypatch: pytest.MonkeyPatch,
    limiter_calls: list[None] | None,
) -> tuple[PostgresResetter, FakeEngine, list[tuple[str, Any]]]:
    log: list[tuple[str, Any]] = []
    engine = FakeEngine(log)
    monkeypatch.setattr(
        reset_module,
        "PostgresUserRepository",
        lambda _engine: FakeRepository("users", log),
    )
    resetter = PostgresResetter(
        engine,  # type: ignore[arg-type]
        customers=FakeRepository("customers", log),  # type: ignore[arg-type]
        orders=FakeRepository("orders", log, restarts=3),  # type: ignore[arg-type]
        invoices=FakeRepository("invoices", log, restarts=4),  # type: ignore[arg-type]
        default_tax_rate=Decimal("10"),
        reset_limiters=None if limiter_calls is None else lambda: limiter_calls.append(None),
    )
    return resetter, engine, log


def test_a_postgres_reset_restores_in_order_and_restarts_the_sequences_last(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    limiter_calls: list[None] = []
    resetter, engine, log = _postgres_resetter(monkeypatch, limiter_calls)

    resetter.reset()

    names = [name for name, _ in log]
    assert engine.transactions == 1
    assert names[0] == "sql"  # The advisory lock is the first statement.
    assert names[1:6] == ["invoices", "orders", "customers", "orders", "invoices"]
    assert names[6] == "users"
    first_restart = next(index for index, name in enumerate(names) if name.startswith("restart-"))
    restarts = names[first_restart:]
    assert len(restarts) == 16
    assert all(name.startswith("restart-") for name in restarts)
    assert restarts[0] == "restart-invoices"
    assert restarts[-1] == "restart-users"
    assert limiter_calls == [None]


def test_a_postgres_reset_without_a_limiter_callable_still_restores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resetter, engine, _ = _postgres_resetter(monkeypatch, None)

    resetter.reset()

    assert engine.transactions == 1


def test_a_postgres_default_seed_restores_the_same_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resetter, engine, log = _postgres_resetter(monkeypatch, [])

    resetter.seed("default")

    names = [name for name, _ in log]
    assert engine.transactions == 1
    assert names[1:4] == ["invoices", "orders", "customers"]
    assert "users" in names
    assert names[-1] == "restart-users"


def test_a_postgres_empty_seed_keeps_the_users_and_the_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resetter, engine, log = _postgres_resetter(monkeypatch, [])

    resetter.seed("empty")

    names = [name for name, _ in log]
    assert engine.transactions == 1
    assert names[1:4] == ["invoices", "orders", "customers"]
    assert names.count("users") == 1
    assert sum(1 for name, _ in log if name == "sql") == 3
    assert names[-1] == "restart-users"


def test_a_postgres_seed_with_an_unknown_dataset_rolls_the_transaction_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resetter, engine, log = _postgres_resetter(monkeypatch, [])

    with pytest.raises(ValueError, match="Unknown dataset: other"):
        resetter.seed("other")  # type: ignore[arg-type]

    assert engine.transactions == 1
    assert [name for name, _ in log] == ["sql"]  # Only the advisory lock ran.
