"""The reset and seed endpoints of the test-only controls."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.customers.models import NewCustomer
from app.modules.testcontrols.models import NewRule

NOW = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)


def _customer_names(app: FastAPI) -> list[str]:
    items, _ = app.state.customer_repository.list(
        query=None,
        status=None,
        page=1,
        page_size=20,
    )
    return [customer.name for customer in items]


def _order_numbers(app: FastAPI) -> list[str]:
    items, _ = app.state.order_store.list_orders(
        query=None,
        status=None,
        customer_id=None,
        page=1,
        page_size=20,
    )
    return [order.number for order, _ in items]


def _fill_general_limiter(app: FastAPI) -> None:
    limiter = app.state.container.limiters.general
    for _ in range(120):
        limiter.hit("test-client")
    assert limiter.hit("test-client").allowed is False


def test_reset_answers_ok(controls_client: TestClient) -> None:
    response = controls_client.post("/__test__/reset")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_seed_answers_the_dataset(controls_client: TestClient) -> None:
    response = controls_client.post("/__test__/seed", json={"dataset": "default"})

    assert response.status_code == 200
    assert response.json() == {"dataset": "default"}

    response = controls_client.post("/__test__/seed", json={"dataset": "empty"})

    assert response.status_code == 200
    assert response.json() == {"dataset": "empty"}


def test_an_unknown_dataset_is_a_validation_error(controls_client: TestClient) -> None:
    response = controls_client.post("/__test__/seed", json={"dataset": "other"})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["errors"] == [
        {
            "field": "dataset",
            "code": "INVALID_FORMAT",
            "message": "El formato no es válido.",
        }
    ]


def test_a_missing_dataset_is_required(controls_client: TestClient) -> None:
    response = controls_client.post("/__test__/seed", json={})

    assert response.status_code == 422
    assert response.json()["errors"] == [
        {
            "field": "dataset",
            "code": "REQUIRED",
            "message": "Este campo es obligatorio.",
        }
    ]


def test_an_unknown_field_is_refused(controls_client: TestClient) -> None:
    response = controls_client.post(
        "/__test__/seed",
        json={"dataset": "default", "unknown": 1},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["errors"][0]["field"] == "unknown"


def test_empty_leaves_no_data_and_restarts_the_sequences(
    controls_app: FastAPI,
    controls_client: TestClient,
) -> None:
    response = controls_client.post("/__test__/seed", json={"dataset": "empty"})

    assert response.status_code == 200
    assert _customer_names(controls_app) == []
    assert _order_numbers(controls_app) == []
    assert controls_app.state.order_store.list_products() == []
    assert controls_app.state.invoice_store.list_invoices(
        query=None,
        status=None,
        order_id=None,
        page=1,
        page_size=20,
    ) == ([], 0)
    assert controls_app.state.order_store.get_tax_rate() == Decimal("10.00")
    assert controls_app.state.clock_store.get() == 0.0
    assert controls_app.state.fault_store.list() == []

    customer = controls_app.state.customer_repository.add(
        NewCustomer("New Customer", "new@example.test", None, None, None),
        NOW,
    )
    order = controls_app.state.order_store.create_order(customer.id, NOW)

    assert customer.id == 1
    assert order.number == "PED-0001"


def test_default_restores_the_data_but_leaves_the_controls_alone(
    controls_app: FastAPI,
    controls_client: TestClient,
) -> None:
    controls_app.state.customer_repository.update(
        1,
        {"name": "Changed"},
        None,
        NOW,
    )
    controls_app.state.clock_store.set(3600)
    controls_app.state.fault_store.add(NewRule(target="gateway", remaining=1))
    _fill_general_limiter(controls_app)

    response = controls_client.post("/__test__/seed", json={"dataset": "default"})

    assert response.status_code == 200
    assert controls_app.state.customer_repository.get(1).name == "Acme Industrial S.A."
    assert controls_app.state.clock_store.get() == 3600.0
    assert [rule.target for rule in controls_app.state.fault_store.list()] == ["gateway"]
    assert controls_app.state.container.limiters.general.hit("test-client").allowed is False
