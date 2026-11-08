"""The request controls ASGI middleware."""

from __future__ import annotations

import logging

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError

from app.config import Settings
from app.guards.request_controls import RequestControlsMiddleware
from app.infra.clock import OffsetClock, SystemClock, clock_offset
from app.modules.testcontrols.controls import RequestControls
from app.modules.testcontrols.memory import (
    InMemoryClockOffsetStore,
    InMemoryFaultStore,
)
from app.modules.testcontrols.models import FaultDecision, NewRule


class SpyControls:
    """Count the loads without changing the in-memory behavior."""

    def __init__(self, clock_store: InMemoryClockOffsetStore, fault_store: InMemoryFaultStore):
        self.inner = RequestControls(clock_store, fault_store)
        self.calls = 0

    @property
    def uses_threadpool(self) -> bool:
        return False

    def load_request_controls(
        self,
        method: str,
        path: str,
    ) -> tuple[float, FaultDecision | None]:
        self.calls += 1
        return self.inner.load_request_controls(method, path)


class FailingControls:
    """Raise the stored error while loading the request controls."""

    def __init__(self, error: BaseException) -> None:
        self.error = error

    @property
    def uses_threadpool(self) -> bool:
        return False

    def load_request_controls(
        self,
        method: str,
        path: str,
    ) -> tuple[float, FaultDecision | None]:
        raise self.error


class Sleeper:
    """Record the latency waits of the middleware."""

    def __init__(self) -> None:
        self.waits: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.waits.append(seconds)


def _inner_app(hits: list[str]) -> FastAPI:
    app = FastAPI()

    @app.get("/api/echo")
    def echo() -> dict[str, object]:
        hits.append("echo")
        return {"offset": clock_offset.get()}

    @app.get("/api/health")
    def health() -> dict[str, str]:
        hits.append("health")
        return {"status": "ok"}

    @app.get("/__test__/probe")
    def probe() -> dict[str, str]:
        hits.append("probe")
        return {"status": "ok"}

    return app


def _build(
    *,
    test_mode: bool = True,
    test_token: str = "",
    controls: object | None = None,
) -> tuple[
    TestClient,
    SpyControls,
    InMemoryClockOffsetStore,
    InMemoryFaultStore,
    Sleeper,
    list[str],
]:
    clock_store = InMemoryClockOffsetStore(OffsetClock(SystemClock()))
    fault_store = InMemoryFaultStore()
    spy = SpyControls(clock_store, fault_store)
    sleeper = Sleeper()
    hits: list[str] = []
    settings = Settings(
        session_secret="test-secret",
        test_mode=test_mode,
        test_token=test_token,
    )
    middleware = RequestControlsMiddleware(
        _inner_app(hits),
        settings=settings,
        controls=controls if controls is not None else spy,  # type: ignore[arg-type]
        sleep=sleeper,
    )
    return TestClient(middleware), spy, clock_store, fault_store, sleeper, hits


def test_without_controls_it_does_no_work() -> None:
    client, spy, _, fault_store, _, _ = _build(test_mode=False)
    fault_store.add(NewRule(target="route", method="GET", path="/api/echo", status=500))

    response = client.get("/api/echo")

    assert response.status_code == 200
    assert spy.calls == 0


def test_a_non_empty_token_enables_the_controls_without_test_mode() -> None:
    client, spy, _, fault_store, _, _ = _build(test_mode=False, test_token="token")

    fault_store.add(NewRule(target="route", method="GET", path="/api/echo", status=500))

    response = client.get("/api/echo")

    assert response.status_code == 500
    assert spy.calls == 1


def test_a_fault_status_answers_without_calling_the_application() -> None:
    client, _, _, fault_store, _, hits = _build()
    fault_store.add(NewRule(target="route", method="GET", path="/api/echo", status=418))

    response = client.get("/api/echo")

    assert response.status_code == 418
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "INJECTED_FAULT"
    assert response.json()["detail"] == "Falla inyectada para pruebas."
    assert hits == []


def test_the_latency_is_awaited_before_the_application() -> None:
    client, _, _, fault_store, sleeper, hits = _build()
    fault_store.add(NewRule(target="route", method="GET", path="/api/echo", latency_ms=250))

    response = client.get("/api/echo")

    assert response.status_code == 200
    assert sleeper.waits == [0.25]
    assert hits == ["echo"]


def test_health_and_the_test_paths_are_exempt() -> None:
    client, spy, _, _, sleeper, hits = _build()

    assert client.get("/api/health").status_code == 200
    assert client.get("/__test__/probe").status_code == 200

    assert sorted(hits) == ["health", "probe"]
    assert spy.calls == 0
    assert sleeper.waits == []


def test_it_sets_the_context_value_for_the_request_only() -> None:
    client, _, clock_store, _, _, _ = _build()
    clock_store.set(90)

    response = client.get("/api/echo")

    assert response.status_code == 200
    assert response.json() == {"offset": 90.0}
    assert clock_offset.get() is None


def test_a_lock_timeout_answers_503_without_the_driver_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    error = DBAPIError("select", {}, psycopg.errors.LockNotAvailable("relation secret_table"))
    client, *_ = _build(controls=FailingControls(error))

    with caplog.at_level(logging.WARNING):
        response = client.get("/api/echo")

    assert response.status_code == 503
    assert response.json()["code"] == "LOCK_TIMEOUT"
    assert response.headers["content-type"] == "application/problem+json"
    assert "DBAPIError" in caplog.text
    assert "55P03" in caplog.text
    assert response.headers["X-Request-Id"] in caplog.text
    assert "secret_table" not in caplog.text


def test_another_database_error_answers_500_without_the_driver_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    error = DBAPIError(
        "select",
        {},
        psycopg.errors.UndefinedTable("relation secret_table does not exist"),
    )
    client, *_ = _build(controls=FailingControls(error))

    with caplog.at_level(logging.ERROR):
        response = client.get("/api/echo")

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
    assert response.headers["content-type"] == "application/problem+json"
    assert "DBAPIError" in caplog.text
    assert "42P01" in caplog.text
    assert response.headers["X-Request-Id"] in caplog.text
    assert "secret_table" not in caplog.text


def test_a_plain_driver_error_is_also_contained(
    caplog: pytest.LogCaptureFixture,
) -> None:
    error = psycopg.OperationalError("connection secret")
    client, *_ = _build(controls=FailingControls(error))

    with caplog.at_level(logging.ERROR):
        response = client.get("/api/echo")

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
    assert "OperationalError" in caplog.text
    assert "unknown" in caplog.text
    assert "connection secret" not in caplog.text
