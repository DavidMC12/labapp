"""A gateway fault consumed by a real payment request."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.modules.auth.seed import DEMO_PASSWORD
from app.modules.invoices.gateway import FakeGateway
from app.modules.invoices.models import InvoiceStatus, PaymentStatus
from app.modules.testcontrols.models import NewRule
from tests.invoices.helpers import assert_problem, card_body, pay


def _app_and_client() -> tuple[FastAPI, TestClient]:
    app = create_app(Settings(session_secret="test-secret", test_mode=True))
    client = TestClient(app)
    response = client.post(
        "/api/auth/login",
        json={"email": "finance@labapp.test", "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    return app, client


def test_a_gateway_rule_fails_one_payment_and_is_consumed() -> None:
    app, client = _app_and_client()
    app.state.fault_store.add(NewRule(target="gateway", remaining=1))

    failed = pay(client, 1, card_body(), key="key-1")

    body = assert_problem(failed, 503, "PAYMENT_GATEWAY_UNAVAILABLE")
    assert body["reason"] == "GATEWAY_UNAVAILABLE"
    invoice = app.state.invoice_store.get_invoice(1)
    assert invoice.status == InvoiceStatus.ISSUED
    assert invoice.payments[-1].status == PaymentStatus.FAILED
    assert app.state.payment_gateway.__class__ is FakeGateway

    approved = pay(client, 1, card_body(), key="key-2")

    assert approved.status_code == 201
    invoice = app.state.invoice_store.get_invoice(1)
    assert invoice.status == InvoiceStatus.PAID
    assert invoice.payments[-1].status == PaymentStatus.APPROVED
    assert app.state.fault_store.list() == []
