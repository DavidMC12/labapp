"""The PostgreSQL reset behind the test-only controls."""

from __future__ import annotations

import secrets
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from threading import Barrier, Event
from time import sleep

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event, select, text
from sqlalchemy.pool import NullPool

from app.config import Settings
from app.infra.db import normalize_database_url
from app.main import create_app
from app.modules.auth.seed import DEMO_PASSWORD
from app.modules.customers.adapters.postgres import PostgresCustomerRepository
from app.modules.customers.models import NewCustomer
from app.modules.invoices.adapters.postgres import PostgresInvoiceStore
from app.modules.invoices.gateway import FakeGateway
from app.modules.invoices.models import PaymentAttempt
from app.modules.orders.adapters.postgres import PostgresOrderStore
from app.modules.orders.tables import orders
from app.modules.testcontrols.reset import PostgresResetter
from tests.invoices.contract_store import respond

NOW = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)
TABLES = (
    "users",
    "sessions",
    "customers",
    "products",
    "orders",
    "order_lines",
    "settings",
    "invoices",
    "invoice_lines",
    "payments",
    "idempotency_keys",
    "fault_rules",
)
SEQUENCES = (
    "users_id_seq",
    "customers_id_seq",
    "orders_id_seq",
    "order_lines_id_seq",
    "invoices_id_seq",
    "invoice_lines_id_seq",
    "payments_id_seq",
    "order_number_seq",
    "invoice_number_seq",
)
COUNT_STATEMENT = text(
    "select (select count(*) from customers), "
    "(select count(*) from orders), "
    "(select count(*) from invoices)"
)


def _settings(database_settings: Settings) -> Settings:
    return database_settings.model_copy(
        update={
            "session_secret": "test-secret",
            "test_mode": True,
            "app_origin": "http://localhost:3000",
        }
    )


@contextmanager
def _app(database_settings: Settings):
    app = create_app(_settings(database_settings))
    try:
        yield app
    finally:
        app.state.engine.dispose()


def _login(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@labapp.test", "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200


def _count(engine: Engine, table: str) -> int:
    with engine.connect() as connection:
        return connection.execute(text(f"select count(*) from {table}")).scalar_one()


def _snapshot(engine: Engine) -> tuple[dict[str, int], dict[str, tuple[int, bool]]]:
    """Read every row count and the state of every sequence."""
    with engine.connect() as connection:
        counts = {
            table: connection.execute(text(f"select count(*) from {table}")).scalar_one()
            for table in TABLES
        }
        sequences = {
            name: tuple(connection.execute(text(f"select last_value, is_called from {name}")).one())
            for name in SEQUENCES
        }
    return counts, sequences


def _add_extra_rows(app) -> None:
    """Leave the database in a non-empty state that differs from the seed."""
    for index in range(3):
        app.state.customer_repository.add(
            NewCustomer(
                f"Extra {index}",
                f"extra-{index}@example.test",
                None,
                None,
                None,
            ),
            NOW,
        )
    app.state.order_store.create_order(1, NOW)
    app.state.invoice_store.issue_invoice(2, None, NOW)


def test_the_reset_is_atomic_for_a_reader(
    database_settings: Settings,
    database_engine: Engine,
) -> None:
    with _app(database_settings) as app:
        app.state.resetter.reset()
        _add_extra_rows(app)
        with database_engine.connect() as connection:
            old = tuple(connection.execute(COUNT_STATEMENT).one())
        stop = Event()
        started = Event()
        triples: list[tuple[int, int, int]] = []
        failures: list[BaseException] = []

        def read() -> None:
            try:
                with database_engine.connect() as connection:
                    while not stop.is_set():
                        triples.append(tuple(connection.execute(COUNT_STATEMENT).one()))
                        started.set()
                        sleep(0.002)
            except BaseException as error:  # pragma: no cover - reported below
                failures.append(error)

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(read)
            try:
                assert started.wait(timeout=10)
                app.state.resetter.reset()
            finally:
                stop.set()
            future.result(timeout=15)

    new = (10, 7, 3)
    assert failures == []
    assert old == (13, 8, 4)
    assert set(triples) <= {old, new}
    assert old in triples
    assert _count(database_engine, "customers") == 10
    assert _count(database_engine, "orders") == 7
    assert _count(database_engine, "invoices") == 3


def test_a_failed_data_step_leaves_the_rows_and_the_sequences(
    database_settings: Settings,
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _app(database_settings) as app:
        app.state.resetter.reset()
        _add_extra_rows(app)
        before = _snapshot(database_engine)

        original = app.state.invoice_store.replace_all
        calls = {"count": 0}

        def fail_on_the_seed_step(*args: object, **kwargs: object) -> None:
            calls["count"] += 1
            if calls["count"] == 2:
                raise RuntimeError("the last data step failed")
            original(*args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(app.state.resetter._invoices, "replace_all", fail_on_the_seed_step)

        with pytest.raises(RuntimeError, match="the last data step failed"):
            app.state.resetter.reset()

        after = _snapshot(database_engine)

    assert calls["count"] == 2
    assert after == before


def test_a_failed_deferred_step_leaves_the_rows_and_the_sequences(
    database_settings: Settings,
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _app(database_settings) as app:
        app.state.resetter.reset()
        _add_extra_rows(app)
        before = _snapshot(database_engine)

        def fail_before_the_first_setval(connection: object, deferred: object) -> None:
            # setval is not undone by a rollback, so the failure must happen before
            # the first restart for the test to assert that nothing changed.
            raise RuntimeError("the deferred step failed")

        monkeypatch.setattr(
            PostgresResetter,
            "_run_deferred",
            staticmethod(fail_before_the_first_setval),
        )

        with pytest.raises(RuntimeError, match="the deferred step failed"):
            app.state.resetter.reset()

        after = _snapshot(database_engine)

    assert after == before


def test_the_reset_keeps_the_sessions(database_settings: Settings) -> None:
    with _app(database_settings) as app:
        app.state.resetter.reset()
        with TestClient(app) as client:
            _login(client)

            app.state.resetter.reset()

            response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "admin@labapp.test"


def test_the_reset_clears_the_instance_rate_limits(database_settings: Settings) -> None:
    with _app(database_settings) as app:
        limiter = app.state.container.limiters.general
        for _ in range(120):
            limiter.hit("test-client")
        assert limiter.hit("test-client").allowed is False

        app.state.resetter.reset()

        assert limiter.hit("test-client").allowed is True


def test_the_sequences_restart_after_a_reset(database_settings: Settings) -> None:
    with _app(database_settings) as app:
        app.state.resetter.reset()

        customer = app.state.customer_repository.add(
            NewCustomer("After Reset", "after-reset@example.test", None, None, None),
            NOW,
        )
        order = app.state.order_store.create_order(1, NOW)
        invoice = app.state.invoice_store.issue_invoice(2, None, NOW)
        payment = app.state.invoice_store.register_payment(
            1,
            key="after-reset",
            fingerprint="after-reset",
            expected_version=None,
            attempt=PaymentAttempt("cash", Decimal("327.80"), None, None),
            respond=respond,
            now=NOW,
        ).response.body

    assert customer.id == 11
    assert order.number == "PED-0008"
    assert invoice.number == "FAC-0004"
    assert payment["payment_id"] == 5


def test_resetting_twice_is_idempotent(
    database_settings: Settings,
    database_engine: Engine,
) -> None:
    with _app(database_settings) as app:
        app.state.resetter.reset()
        first = {table: _count(database_engine, table) for table in TABLES}

        app.state.resetter.reset()
        second = {table: _count(database_engine, table) for table in TABLES}

        with database_engine.connect() as connection:
            clock = connection.execute(
                text("select value from settings where key = 'clock_offset_seconds'")
            ).scalar_one()
            tax_rate = connection.execute(
                text("select value from settings where key = 'tax_rate'")
            ).scalar_one()

    assert first == second
    assert first["customers"] == 10
    assert first["products"] == 15
    assert first["orders"] == 7
    assert first["invoices"] == 3
    assert first["payments"] == 4
    assert first["users"] == 4
    assert first["fault_rules"] == 0
    assert clock == "0"
    assert Decimal(tax_rate) == Decimal("10.00")


def test_two_concurrent_resets_both_finish(database_settings: Settings) -> None:
    with _app(database_settings) as first, _app(database_settings) as second:
        barrier = Barrier(2)

        def reset(app) -> str:
            barrier.wait()
            app.state.resetter.reset()
            return "done"

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(reset, app) for app in (first, second)]
            outcomes = [future.result(timeout=30) for future in futures]

        response = TestClient(first).get("/api/health")

    assert outcomes == ["done", "done"]
    assert response.status_code == 200


def test_the_reset_keeps_the_invoice_links(
    database_settings: Settings,
    database_engine: Engine,
) -> None:
    with _app(database_settings) as app:
        app.state.resetter.reset()
        issued = app.state.invoice_store.issue_invoice(2, None, NOW)
        app.state.invoice_store.register_payment(
            issued.id,
            key="links",
            fingerprint="links",
            expected_version=None,
            attempt=PaymentAttempt("cash", Decimal("121.00"), None, None),
            respond=respond,
            now=NOW,
        )

        app.state.resetter.reset()

        with database_engine.connect() as connection:
            links = connection.execute(
                select(orders.c.id, orders.c.invoice_id, orders.c.version).order_by(orders.c.id)
            ).all()

    assert [(row.id, row.invoice_id, row.version) for row in links][2:5] == [
        (3, 1, 1),
        (4, 2, 1),
        (5, 3, 1),
    ]


def test_the_reset_leaves_a_decoy_schema_untouched(database_settings: Settings) -> None:
    real = database_settings.database_schema
    decoy = f"t_decoy_{secrets.token_hex(6)}"
    assert real is not None
    bootstrap = create_engine(
        normalize_database_url(database_settings.database_url),
        poolclass=NullPool,
        hide_parameters=True,
    )
    quoted_decoy = bootstrap.dialect.identifier_preparer.quote_schema(decoy)
    quoted_real = bootstrap.dialect.identifier_preparer.quote_schema(real)
    try:
        with bootstrap.begin() as connection:
            connection.exec_driver_sql(f"CREATE SCHEMA {quoted_decoy}")
            for table in TABLES:
                connection.exec_driver_sql(
                    f"CREATE TABLE {quoted_decoy}.{table} "
                    f"(LIKE {quoted_real}.{table} INCLUDING ALL)"
                )
            connection.exec_driver_sql(
                f"INSERT INTO {quoted_decoy}.customers "
                "(id, name, email, status, version, created_at, updated_at, "
                "name_search, email_search) VALUES "
                "(999, 'Sentinel', 'sentinel@example.test', 'active', 1, now(), now(), "
                "'sentinel', 'sentinel@example.test')"
            )
            connection.exec_driver_sql(
                f"INSERT INTO {quoted_decoy}.settings (key, value) VALUES "
                "('clock_offset_seconds', '999'), ('tax_rate', '99.00')"
            )
            connection.exec_driver_sql(
                f"INSERT INTO {quoted_decoy}.fault_rules "
                "(target, method, path, latency_ms, status, remaining) VALUES "
                "('route', 'GET', '/sentinel', 0, 500, null)"
            )

        engine = create_engine(
            normalize_database_url(database_settings.database_url),
            poolclass=NullPool,
            hide_parameters=True,
            connect_args={"options": f"-c search_path={decoy}"},
        ).execution_options(schema_translate_map={None: real})
        event.listen(
            engine,
            "begin",
            lambda connection: connection.exec_driver_sql("SET LOCAL lock_timeout = 5000"),
        )
        try:
            resetter = PostgresResetter(
                engine,
                customers=PostgresCustomerRepository(engine),
                orders=PostgresOrderStore(engine),
                invoices=PostgresInvoiceStore(engine, FakeGateway()),
                default_tax_rate=Decimal("10"),
            )
            resetter.reset()
        finally:
            engine.dispose()

        with bootstrap.connect() as connection:
            sentinel = connection.execute(
                text(f"select name from {quoted_decoy}.customers where id = 999")
            ).scalar_one()
            clock = connection.execute(
                text(
                    f"select value from {quoted_decoy}.settings where key = 'clock_offset_seconds'"
                )
            ).scalar_one()
            faults = connection.execute(
                text(f"select count(*) from {quoted_decoy}.fault_rules")
            ).scalar_one()
            real_customers = connection.execute(
                text(f"select count(*) from {quoted_real}.customers")
            ).scalar_one()

        assert sentinel == "Sentinel"
        assert clock == "999"
        assert faults == 1
        assert real_customers == 10
    finally:
        with bootstrap.begin() as connection:
            connection.exec_driver_sql(f"DROP SCHEMA IF EXISTS {quoted_decoy} CASCADE")
        bootstrap.dispose()
