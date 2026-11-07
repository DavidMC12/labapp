"""The literal examples of the Invoices and payments API subsection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.config import Settings
from app.infra.clock import OffsetClock
from app.main import create_app
from app.modules.auth.seed import DEMO_PASSWORD
from tests.infra.helpers import FixedClock

INVOICE_EXAMPLE = {
    "id": 4,
    "number": "FAC-0004",
    "status": "issued",
    "order_id": 2,
    "order_number": "PED-0002",
    "customer": {
        "id": 2,
        "name": "Beta Comercial Ltda.",
        "tax_id": "BETA-800456",
        "address": None,
    },
    "lines": [
        {
            "id": 4,
            "product_id": 2,
            "sku": "MS-200",
            "name": "Mouse óptico",
            "quantity": 5,
            "unit_price": "9.50",
            "line_total": "47.50",
        },
        {
            "id": 5,
            "product_id": 6,
            "sku": "CB-010",
            "name": "Cable HDMI 2 m",
            "quantity": 10,
            "unit_price": "6.25",
            "line_total": "62.50",
        },
    ],
    "subtotal": "110.00",
    "tax_rate": "10.00",
    "tax": "11.00",
    "total": "121.00",
    "payments": [],
    "version": 1,
    "created_at": "2026-11-05T15:00:00Z",
    "updated_at": "2026-11-05T15:00:00Z",
}

PAYMENT_RESULT_EXAMPLE = {
    "payment": {
        "id": 5,
        "method": "card",
        "status": "approved",
        "amount": "121.00",
        "reference": None,
        "card_last4": "4242",
        "reason": None,
        "created_at": "2026-11-05T15:02:00Z",
    },
    "invoice": {
        "id": 4,
        "number": "FAC-0004",
        "status": "paid",
        "order_id": 2,
        "order_number": "PED-0002",
        "customer": {
            "id": 2,
            "name": "Beta Comercial Ltda.",
            "tax_id": "BETA-800456",
            "address": None,
        },
        "lines": [
            {
                "id": 4,
                "product_id": 2,
                "sku": "MS-200",
                "name": "Mouse óptico",
                "quantity": 5,
                "unit_price": "9.50",
                "line_total": "47.50",
            },
            {
                "id": 5,
                "product_id": 6,
                "sku": "CB-010",
                "name": "Cable HDMI 2 m",
                "quantity": 10,
                "unit_price": "6.25",
                "line_total": "62.50",
            },
        ],
        "subtotal": "110.00",
        "tax_rate": "10.00",
        "tax": "11.00",
        "total": "121.00",
        "payments": [
            {
                "id": 5,
                "method": "card",
                "status": "approved",
                "amount": "121.00",
                "reference": None,
                "card_last4": "4242",
                "reason": None,
                "created_at": "2026-11-05T15:02:00Z",
            }
        ],
        "version": 2,
        "created_at": "2026-11-05T15:00:00Z",
        "updated_at": "2026-11-05T15:02:00Z",
    },
}

DECLINED_EXAMPLE = {
    "type": "about:blank",
    "title": "Payment Required",
    "status": 402,
    "code": "PAYMENT_DECLINED",
    "detail": "La pasarela rechazó el pago. Prueba con otra tarjeta.",
    "payment_id": 5,
    "reason": "CARD_DECLINED",
}


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
    assert issued.json() == INVOICE_EXAMPLE

    clock.advance(timedelta(minutes=2))
    payment = client.post(
        "/api/invoices/4/payments",
        json={
            "method": "card",
            "amount": "121.00",
            "card": {"number": "4242 4242 4242 4242", "expiry": "12/30", "cvc": "123"},
        },
        headers={"Idempotency-Key": "pay-0001"},
    )

    assert payment.status_code == 201
    assert payment.headers["etag"] == '"2"'
    assert payment.json() == PAYMENT_RESULT_EXAMPLE

    replay = client.post(
        "/api/invoices/4/payments",
        json={
            "method": "card",
            "amount": "121.00",
            "card": {"number": "4242 4242 4242 4242", "expiry": "12/30", "cvc": "123"},
        },
        headers={"Idempotency-Key": "pay-0001"},
    )

    assert replay.status_code == 201
    assert replay.headers["idempotency-replayed"] == "true"
    assert replay.json() == PAYMENT_RESULT_EXAMPLE
    assert client.get("/api/orders/2").json()["status"] == "paid"


def test_the_documented_declined_payment_is_reproduced_literally() -> None:
    app, _ = _app()
    client = _client(app)

    response = client.post(
        "/api/invoices/1/payments",
        json={
            "method": "card",
            "amount": "327.80",
            "card": {"number": "4000 0000 0000 0002", "expiry": "12/30", "cvc": "123"},
        },
        headers={"Idempotency-Key": "pay-0002"},
    )

    assert response.status_code == 402
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == DECLINED_EXAMPLE
    invoice = client.get("/api/invoices/1").json()
    assert invoice["status"] == "issued"
    assert invoice["payments"][-1]["id"] == 5
