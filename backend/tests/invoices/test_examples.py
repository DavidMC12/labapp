"""The literal examples of the Invoices and payments API subsection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.config import Settings
from app.infra.clock import OffsetClock
from app.main import create_app
from app.modules.auth.seed import DEMO_PASSWORD
from app.openapi_examples import (
    CARD_APPROVED_REQUEST,
    CARD_DECLINED_REQUEST,
    INVOICE_ISSUED_201,
    PAYMENT_APPROVED_201,
    PAYMENT_DECLINED_402,
)
from tests.infra.helpers import FixedClock


def _app() -> tuple[object, OffsetClock]:
    clock = OffsetClock(FixedClock(datetime(2026, 11, 5, 15, 0, tzinfo=UTC)))
    app = create_app(
        Settings(
            session_secret="test-secret",
            test_mode=False,
            app_origin="http://localhost:3000",
        ),
        clock=clock,
    )
    return app, clock


def _client(app: object) -> TestClient:
    client = TestClient(app)  # type: ignore[arg-type]
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "finance@labapp.test", "password": DEMO_PASSWORD},
        ).status_code
        == 200
    )
    return client


def test_the_documented_issue_and_payment_are_reproduced_literally() -> None:
    app, clock = _app()
    client = _client(app)

    issued = client.post("/api/orders/2/invoice")

    assert issued.status_code == 201
    assert issued.headers["location"] == "/api/invoices/4"
    assert issued.headers["etag"] == '"1"'
    assert issued.json() == INVOICE_ISSUED_201

    clock.advance(timedelta(minutes=2))
    payment = client.post(
        "/api/invoices/4/payments",
        json=CARD_APPROVED_REQUEST,
        headers={"Idempotency-Key": "pay-0001"},
    )

    assert payment.status_code == 201
    assert payment.headers["etag"] == '"2"'
    assert payment.json() == PAYMENT_APPROVED_201

    replay = client.post(
        "/api/invoices/4/payments",
        json=CARD_APPROVED_REQUEST,
        headers={"Idempotency-Key": "pay-0001"},
    )

    assert replay.status_code == 201
    assert replay.headers["idempotency-replayed"] == "true"
    assert replay.json() == PAYMENT_APPROVED_201
    assert client.get("/api/orders/2").json()["status"] == "paid"


def test_the_documented_declined_payment_is_reproduced_literally() -> None:
    app, _ = _app()
    client = _client(app)

    response = client.post(
        "/api/invoices/1/payments",
        json=CARD_DECLINED_REQUEST,
        headers={"Idempotency-Key": "pay-0002"},
    )

    assert response.status_code == 402
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == PAYMENT_DECLINED_402
    invoice = client.get("/api/invoices/1").json()
    assert invoice["status"] == "issued"
    assert invoice["payments"][-1]["id"] == 5
