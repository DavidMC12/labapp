"""The adapters can defer their sequence restarts to the caller."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection

from app.modules.auth.adapters.postgres import PostgresUserRepository
from app.modules.customers.adapters.postgres import PostgresCustomerRepository
from app.modules.invoices.adapters.postgres import PostgresInvoiceStore
from app.modules.invoices.gateway import FakeGateway
from app.modules.orders.adapters.postgres import PostgresOrderStore

URL = "postgresql+psycopg://user@localhost/database"


class Recorder:
    """Record the statements without opening a connection."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def execute(self, statement: object, parameters: object = None) -> None:
        self.calls.append((str(statement), parameters))

    def setval_calls(self) -> list[tuple[str, Any]]:
        return [call for call in self.calls if "setval" in call[0]]


def _engine():
    return create_engine(URL)


def _run_deferred(
    deferred: list[Callable[[Connection], None]],
    recorder: Recorder,
) -> None:
    for restart in deferred:
        restart(recorder)  # type: ignore[arg-type]


def test_the_customer_repository_defers_its_id_sequence() -> None:
    recorder = Recorder()
    deferred: list[Callable[[Connection], None]] = []

    PostgresCustomerRepository(_engine()).replace_all(
        [],
        connection=recorder,  # type: ignore[arg-type]
        defer_sequences=deferred,
    )

    assert recorder.setval_calls() == []
    assert len(deferred) == 1

    _run_deferred(deferred, recorder)

    assert len(recorder.setval_calls()) == 1


def test_the_order_store_defers_its_three_sequences() -> None:
    recorder = Recorder()
    deferred: list[Callable[[Connection], None]] = []

    PostgresOrderStore(_engine()).replace_all(
        [],
        [],
        Decimal("10"),
        connection=recorder,  # type: ignore[arg-type]
        defer_sequences=deferred,
    )

    assert recorder.setval_calls() == []
    assert len(deferred) == 3

    _run_deferred(deferred, recorder)

    assert len(recorder.setval_calls()) == 3


def test_the_invoice_store_defers_its_four_sequences() -> None:
    recorder = Recorder()
    deferred: list[Callable[[Connection], None]] = []

    PostgresInvoiceStore(_engine(), FakeGateway()).replace_all(
        [],
        [],
        connection=recorder,  # type: ignore[arg-type]
        defer_sequences=deferred,
    )

    assert recorder.setval_calls() == []
    assert len(deferred) == 4

    _run_deferred(deferred, recorder)

    assert len(recorder.setval_calls()) == 4


def test_the_user_repository_defers_its_id_sequence() -> None:
    recorder = Recorder()
    deferred: list[Callable[[Connection], None]] = []

    PostgresUserRepository(_engine()).replace_all(
        [],
        connection=recorder,  # type: ignore[arg-type]
        defer_sequences=deferred,
    )

    assert recorder.setval_calls() == []
    assert len(deferred) == 1

    _run_deferred(deferred, recorder)

    assert len(recorder.setval_calls()) == 1
