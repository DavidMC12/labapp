"""A reset restores every module and keeps the sessions."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.orders import OrderAction, OrderStatus
from app.modules.testcontrols.models import NewRule

from .helpers import login

NOW = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)


def _fill_general_limiter(app: FastAPI) -> None:
    limiter = app.state.container.limiters.general
    for _ in range(120):
        limiter.hit("test-client")
    assert limiter.hit("test-client").allowed is False


def test_reset_restores_every_module_and_keeps_the_session(
    controls_app: FastAPI,
    controls_client: TestClient,
) -> None:
    login(controls_client)
    controls_app.state.customer_repository.update(1, {"name": "Changed"}, None, NOW)
    controls_app.state.order_store.transition(1, OrderAction.CONFIRM, None, NOW)
    issued = controls_app.state.invoices.issue(2, None)
    controls_app.state.order_store.set_tax_rate(Decimal("20"))
    controls_app.state.clock_store.set(3600)
    controls_app.state.fault_store.add(NewRule(target="gateway", remaining=1))
    _fill_general_limiter(controls_app)

    assert controls_app.state.customer_repository.get(1).name == "Changed"
    assert controls_app.state.order_store.get_order(1).status == OrderStatus.CONFIRMED
    assert controls_app.state.invoice_store.get_invoice(issued.id) is not None
    assert controls_app.state.order_store.get_product(1).stock == 118
    assert controls_app.state.order_store.get_tax_rate() == Decimal("20.00")

    response = controls_client.post("/__test__/reset")

    assert response.status_code == 200
    customer = controls_app.state.customer_repository.get(1)
    assert customer is not None
    assert customer.name == "Acme Industrial S.A."
    assert customer.version == 1
    order = controls_app.state.order_store.get_order(1)
    assert order is not None
    assert order.status == OrderStatus.DRAFT
    assert order.version == 1
    assert controls_app.state.invoice_store.get_invoice(issued.id) is None
    assert (
        controls_app.state.invoice_store.list_invoices(
            query=None,
            status=None,
            order_id=None,
            page=1,
            page_size=20,
        )[1]
        == 3
    )
    assert controls_app.state.order_store.get_product(1).stock == 120
    assert controls_app.state.order_store.get_tax_rate() == Decimal("10.00")
    assert controls_app.state.clock_store.get() == 0.0
    assert controls_app.state.fault_store.list() == []
    assert controls_app.state.container.limiters.general.hit("test-client").allowed is True

    session = controls_client.get("/api/auth/me")

    assert session.status_code == 200
    assert session.json()["email"] == "admin@labapp.test"
