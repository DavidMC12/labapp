"""Unit tests for the idempotency claim of the PostgreSQL invoice store."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import Delete, Insert, Select

from app.errors import ApiError
from app.modules.invoices.adapters.postgres import PostgresInvoiceStore
from app.modules.invoices.gateway import FakeGateway

NOW = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)


class _Result:
    """The small part of a SQLAlchemy result the claim uses."""

    def __init__(self, row: dict[str, object] | None = None) -> None:
        self._row = row

    def first(self) -> dict[str, object] | None:
        return self._row

    def mappings(self) -> _Result:
        return self


class _VanishingClaimConnection:
    """A fake connection whose conflicting row disappears after ``empty_reads``."""

    def __init__(self, empty_reads: int) -> None:
        self._empty_reads = empty_reads
        self.inserts = 0
        self.selects = 0

    def execute(self, statement: object) -> _Result:
        if isinstance(statement, Delete):
            return _Result()
        if isinstance(statement, Insert):
            self.inserts += 1
            if self.selects < self._empty_reads:
                return _Result()
            return _Result({"key": "key-1"})
        if isinstance(statement, Select):
            self.selects += 1
            return _Result()
        raise AssertionError(f"unexpected statement: {statement!r}")


def _store() -> PostgresInvoiceStore:
    return PostgresInvoiceStore(None, FakeGateway())  # type: ignore[arg-type]


def test_a_claim_retries_when_the_conflicting_row_disappears() -> None:
    connection = _VanishingClaimConnection(empty_reads=1)

    outcome = _store()._claim_key(connection, 1, "key-1", "fp-1", NOW)  # type: ignore[arg-type]

    assert outcome is None
    assert connection.inserts == 2
    assert connection.selects == 1


def test_a_claim_that_never_finds_the_conflicting_row_is_a_lock_timeout() -> None:
    connection = _VanishingClaimConnection(empty_reads=3)

    with pytest.raises(ApiError) as error:
        _store()._claim_key(connection, 1, "key-1", "fp-1", NOW)  # type: ignore[arg-type]

    assert error.value.status == 503
    assert error.value.code == "LOCK_TIMEOUT"
    assert connection.inserts == 3
    assert connection.selects == 3
