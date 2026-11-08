"""Tests for the per-request loader of the clock and the faults."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from app.modules.testcontrols.controls import RequestControls
from app.modules.testcontrols.models import FaultDecision


class RecordingClockStore:
    def __init__(self, offset: float) -> None:
        self.offset = offset
        self.connections: list[object] = []

    def get(self, connection: object = None) -> float:
        self.connections.append(connection)
        return self.offset


class RecordingFaultStore:
    def __init__(self, decision: FaultDecision | None) -> None:
        self.decision = decision
        self.calls: list[tuple[str, str, object]] = []

    def take(
        self,
        method: str,
        path: str,
        connection: object = None,
    ) -> FaultDecision | None:
        self.calls.append((method, path, connection))
        return self.decision


class FakeEngine:
    def __init__(self) -> None:
        self.connection = object()
        self.transactions = 0

    @contextmanager
    def begin(self) -> Iterator[Any]:
        self.transactions += 1
        yield self.connection


def test_in_memory_mode_reads_the_stores_without_a_connection() -> None:
    clock = RecordingClockStore(12.5)
    fault = RecordingFaultStore(FaultDecision(status=500, latency_ms=0))
    controls = RequestControls(clock, fault)  # type: ignore[arg-type]

    offset, decision = controls.load_request_controls("GET", "/api/customers")

    assert controls.uses_threadpool is False
    assert offset == 12.5
    assert decision == FaultDecision(status=500, latency_ms=0)
    assert clock.connections == [None]
    assert fault.calls == [("GET", "/api/customers", None)]


def test_postgres_mode_reads_both_stores_inside_one_transaction() -> None:
    engine = FakeEngine()
    clock = RecordingClockStore(3.0)
    fault = RecordingFaultStore(None)
    controls = RequestControls(clock, fault, engine)  # type: ignore[arg-type]

    offset, decision = controls.load_request_controls("POST", "/api/orders")

    assert controls.uses_threadpool is True
    assert offset == 3.0
    assert decision is None
    assert engine.transactions == 1
    assert clock.connections == [engine.connection]
    assert fault.calls == [("POST", "/api/orders", engine.connection)]
