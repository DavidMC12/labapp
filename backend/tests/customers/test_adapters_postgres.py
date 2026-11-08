"""Unit tests for the PostgreSQL customer adapter that need no database."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.dialects import postgresql

from app.modules.customers.adapters.postgres import PostgresCustomerRepository
from app.modules.customers.models import NewCustomer

NOW = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)


class FakeResult:
    """The rows that the recorded statement returns."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def mappings(self) -> FakeResult:
        return self

    def all(self) -> list[dict[str, Any]]:
        return self.rows


class FakeConnection:
    """Record the statements of one transaction."""

    def __init__(self, statements: list[Any], rows: list[dict[str, Any]]) -> None:
        self.statements = statements
        self.rows = rows

    def execute(self, statement: Any) -> FakeResult:
        self.statements.append(statement)
        return FakeResult(self.rows)


class FakeEngine:
    """Yield one recording connection per transaction."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.statements: list[Any] = []
        self.rows = rows
        self.transactions = 0

    @contextmanager
    def begin(self) -> Iterator[FakeConnection]:
        self.transactions += 1
        yield FakeConnection(self.statements, self.rows)


def stored_row(identifier: int, name: str, email: str) -> dict[str, Any]:
    return {
        "id": identifier,
        "name": name,
        "email": email,
        "phone": None,
        "tax_id": None,
        "address": None,
        "status": "active",
        "version": 1,
        "created_at": NOW,
        "updated_at": NOW,
        "name_search": name.lower(),
        "email_search": email.lower(),
    }


def test_add_many_inserts_the_batch_into_the_customers_table() -> None:
    # A parameter that shadows the module-level ``customers`` table would make
    # ``insert(customers)`` fail before it reaches the database.
    engine = FakeEngine(
        [
            stored_row(1, "One", "one@example.test"),
            stored_row(2, "Two", "two@example.test"),
        ]
    )
    repository = PostgresCustomerRepository(engine)  # type: ignore[arg-type]

    created = repository.add_many(
        [
            NewCustomer(
                name="One",
                email="one@example.test",
                phone=None,
                tax_id=None,
                address=None,
            ),
            NewCustomer(
                name="Two",
                email="two@example.test",
                phone=None,
                tax_id=None,
                address=None,
            ),
        ],
        NOW,
    )

    assert [item.id for item in created] == [1, 2]
    assert engine.transactions == 1
    assert len(engine.statements) == 1
    compiled = str(engine.statements[0].compile(dialect=postgresql.dialect()))
    assert compiled.startswith("INSERT INTO customers")
    assert "RETURNING" in compiled
    values = compiled.split(" VALUES ", 1)[1].split(" RETURNING ", 1)[0]
    assert values.count("), (") == 1
