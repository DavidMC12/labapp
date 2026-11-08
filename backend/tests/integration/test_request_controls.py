"""The PostgreSQL clock and fault stores shared by several instances."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, insert

from app.cli import seed_database
from app.config import Settings
from app.main import create_app
from app.modules.auth.seed import DEMO_PASSWORD
from app.modules.invoices.adapters.postgres import PostgresInvoiceStore
from app.modules.invoices.gateway import FakeGateway, FaultyGateway
from app.modules.invoices.models import PaymentAttempt, PaymentStatus
from app.modules.testcontrols.models import NewRule
from app.modules.testcontrols.postgres import (
    PostgresClockOffsetStore,
    PostgresFaultStore,
)
from app.modules.testcontrols.tables import fault_rules
from tests.invoices.contract_store import respond

NOW = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)
NINE_HOURS = 9 * 60 * 60


def _settings(database_settings: Settings) -> Settings:
    return database_settings.model_copy(
        update={
            "session_secret": "test-secret",
            "test_mode": True,
            "app_origin": "http://localhost:3000",
        }
    )


@contextmanager
def _two_instances(database_settings: Settings):
    first = create_app(_settings(database_settings))
    second = create_app(_settings(database_settings))
    try:
        yield first, second
    finally:
        first.state.engine.dispose()
        second.state.engine.dispose()


def _login(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "finance@labapp.test", "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200


def test_the_offset_round_trips_and_advances_from_an_absent_row(
    db,
    unpinned_database_engine: Engine,
) -> None:
    store = PostgresClockOffsetStore(unpinned_database_engine)

    assert store.get() == 0.0
    assert store.advance(7.5) == pytest.approx(7.5)
    assert store.get() == pytest.approx(7.5)
    store.set(1.25)
    assert store.get() == pytest.approx(1.25)


def test_two_concurrent_advances_add_up(
    db,
    unpinned_database_engine: Engine,
) -> None:
    first = PostgresClockOffsetStore(unpinned_database_engine)
    second = PostgresClockOffsetStore(unpinned_database_engine)
    first.set(100.0)
    barrier = Barrier(2)

    def advance(store: PostgresClockOffsetStore) -> float:
        barrier.wait()
        return store.advance(12.5)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(advance, store) for store in (first, second)]
        results = [future.result(timeout=15) for future in futures]

    assert sorted(results) == pytest.approx([112.5, 125.0])
    assert first.get() == pytest.approx(125.0)


def test_two_concurrent_advances_on_an_absent_row_add_up(
    db,
    unpinned_database_engine: Engine,
) -> None:
    first = PostgresClockOffsetStore(unpinned_database_engine)
    second = PostgresClockOffsetStore(unpinned_database_engine)
    barrier = Barrier(2)

    def advance(store: PostgresClockOffsetStore) -> float:
        barrier.wait()
        return store.advance(12.5)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(advance, store) for store in (first, second)]
        results = [future.result(timeout=15) for future in futures]

    assert sorted(results) == pytest.approx([12.5, 25.0])
    assert first.get() == pytest.approx(25.0)


def test_an_offset_set_by_one_instance_is_seen_by_the_other(
    db,
    database_settings: Settings,
) -> None:
    seed_database(database_settings)
    with _two_instances(database_settings) as (first, second):
        first.state.clock_store.set(NINE_HOURS)
        with TestClient(second) as client:
            _login(client)
            first.state.clock_store.advance(NINE_HOURS)

            response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "SESSION_EXPIRED"


def test_a_fault_added_by_one_instance_applies_on_the_other(
    db,
    database_settings: Settings,
) -> None:
    seed_database(database_settings)
    with _two_instances(database_settings) as (first, second):
        first.state.fault_store.add(
            NewRule(
                target="route",
                method="GET",
                path="/api/auth/me",
                status=418,
                remaining=1,
            )
        )
        with TestClient(second) as client:
            injected = client.get("/api/auth/me")
            normal = client.get("/api/auth/me")

    assert injected.status_code == 418
    assert injected.json()["code"] == "INJECTED_FAULT"
    assert normal.status_code == 401
    assert normal.json()["code"] == "UNAUTHENTICATED"


def test_only_the_remaining_count_of_concurrent_requests_is_injected(
    db,
    database_settings: Settings,
) -> None:
    seed_database(database_settings)
    app = create_app(_settings(database_settings))
    app.state.fault_store.add(
        NewRule(
            target="route",
            method="GET",
            path="/api/auth/me",
            status=418,
            remaining=3,
        )
    )
    barrier = Barrier(8)

    def request() -> int:
        barrier.wait()
        with TestClient(app) as client:
            return client.get("/api/auth/me").status_code

    try:
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(request) for _ in range(8)]
            codes = [future.result(timeout=30) for future in futures]
    finally:
        app.state.engine.dispose()

    assert codes.count(418) == 3
    assert codes.count(401) == 5


def test_two_concurrent_adds_at_49_leave_at_most_50(
    db,
    unpinned_database_engine: Engine,
) -> None:
    db.execute(
        insert(fault_rules).values(
            [
                {
                    "target": "route",
                    "method": "GET",
                    "path": f"/api/{index}",
                    "latency_ms": 0,
                    "status": 500,
                    "remaining": None,
                }
                for index in range(49)
            ]
        )
    )
    db.commit()
    first = PostgresFaultStore(unpinned_database_engine)
    second = PostgresFaultStore(unpinned_database_engine)
    barrier = Barrier(2)

    def add(store: PostgresFaultStore, index: int) -> str:
        barrier.wait()
        try:
            store.add(
                NewRule(
                    target="route",
                    method="GET",
                    path=f"/api/new-{index}",
                    status=500,
                )
            )
        except Exception as error:  # noqa: BLE001 - the exception type is the assertion
            return type(error).__name__
        return "added"

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(add, store, index) for index, store in enumerate((first, second))
        ]
        outcomes = [future.result(timeout=15) for future in futures]

    assert sorted(outcomes) == ["TooManyFaultRules", "added"]
    assert len(first.list()) == 50


def test_a_gateway_rule_is_consumed_by_one_of_two_concurrent_payments(
    db,
    unpinned_database_engine: Engine,
    postgres_invoice_store: PostgresInvoiceStore,
) -> None:
    fault_store = PostgresFaultStore(unpinned_database_engine)
    fault_store.add(NewRule(target="gateway", remaining=1))
    gateway = FaultyGateway(FakeGateway(), fault_store, sleep=lambda seconds: None)
    store = PostgresInvoiceStore(unpinned_database_engine, gateway)
    other = store.issue_invoice(2, None, NOW)
    barrier = Barrier(2)

    def pay(invoice_id: int, amount: str, key: str) -> None:
        barrier.wait()
        store.register_payment(
            invoice_id,
            key=key,
            fingerprint=key,
            expected_version=None,
            attempt=PaymentAttempt("cash", Decimal(amount), None, None),
            respond=respond,
            now=NOW,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(pay, 1, "327.80", "key-1"),
            executor.submit(pay, other.id, "121.00", "key-2"),
        ]
        for future in futures:
            future.result(timeout=15)

    statuses = [
        store.get_invoice(1).payments[-1].status,
        store.get_invoice(other.id).payments[-1].status,
    ]
    assert sorted(statuses) == [PaymentStatus.APPROVED, PaymentStatus.FAILED]
    assert fault_store.list() == []
