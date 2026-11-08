"""Tests for the order transitions."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.customers.models import CustomerStatus
from tests.orders.helpers import (
    add_line_payload,
    assert_field_error,
    assert_problem,
    change_customer_payload,
    create_order_payload,
)


def _deactivate(app: FastAPI, customer_id: int = 1) -> None:
    app.state.customer_repository.set_status(
        customer_id, CustomerStatus.INACTIVE, None, datetime.now(UTC)
    )


def _stock(client: TestClient, product_id: int) -> int:
    items = client.get("/api/products").json()["items"]
    return next(item["stock"] for item in items if item["id"] == product_id)


def _draft_with_line(client: TestClient) -> dict[str, object]:
    created = client.post("/api/orders", json=create_order_payload(1))
    assert created.status_code == 201
    order_id = created.json()["id"]
    added = client.post(f"/api/orders/{order_id}/lines", json=add_line_payload(1, 2, 1))
    assert added.status_code == 201
    return added.json()


def test_confirm_decrements_stock_and_sets_the_etag(clients: dict[str, TestClient]) -> None:
    order = _draft_with_line(clients["sales"])

    response = clients["sales"].post(
        f"/api/orders/{order['id']}/confirm", headers={"If-Match": '"2"'}
    )

    assert response.status_code == 200
    assert response.headers["etag"] == '"3"'
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["version"] == 3
    assert body["tax_rate"] == "10.00"
    assert _stock(clients["sales"], 1) == 118


def test_confirming_an_empty_order_is_rejected(clients: dict[str, TestClient]) -> None:
    created = clients["sales"].post("/api/orders", json=create_order_payload(1))

    response = clients["sales"].post(f"/api/orders/{created.json()['id']}/confirm")

    body = assert_problem(response, 422, "ORDER_EMPTY")
    assert body["detail"] == "El pedido debe tener al menos una línea."


def test_confirming_lists_every_shortage_and_changes_nothing(
    clients: dict[str, TestClient],
) -> None:
    created = clients["sales"].post("/api/orders", json=create_order_payload(1))
    order_id = created.json()["id"]
    clients["sales"].post(f"/api/orders/{order_id}/lines", json=add_line_payload(7, 4, 1))
    clients["sales"].post(f"/api/orders/{order_id}/lines", json=add_line_payload(9, 1, 2))
    before = clients["sales"].get(f"/api/orders/{order_id}").json()

    response = clients["sales"].post(f"/api/orders/{order_id}/confirm")

    body = assert_problem(response, 409, "INSUFFICIENT_STOCK")
    assert body["detail"] == (
        "No hay stock suficiente de Cámara web HD: disponible 3, solicitado 4."
    )
    assert body["shortages"] == [
        {
            "product_id": 7,
            "sku": "WC-720",
            "name": "Cámara web HD",
            "available": 3,
            "requested": 4,
        },
        {
            "product_id": 9,
            "sku": "PR-400",
            "name": "Impresora láser",
            "available": 0,
            "requested": 1,
        },
    ]
    assert _stock(clients["sales"], 7) == 3
    assert _stock(clients["sales"], 9) == 0
    assert clients["sales"].get(f"/api/orders/{order_id}").json() == before


def test_confirming_requires_an_active_customer(
    clients: dict[str, TestClient], app: FastAPI
) -> None:
    order = _draft_with_line(clients["sales"])
    _deactivate(app, 1)

    assert_problem(
        clients["sales"].post(f"/api/orders/{order['id']}/confirm"),
        422,
        "CUSTOMER_INACTIVE",
    )


def test_cancelling_a_draft_changes_no_stock_and_freezes_the_current_rate(
    clients: dict[str, TestClient],
) -> None:
    clients["admin"].patch("/api/settings", json={"tax_rate": "7"})

    response = clients["sales"].post("/api/orders/1/cancel")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "cancelled"
    assert body["tax_rate"] == "7.00"
    assert body["tax"] == "2.79"
    assert body["total"] == "42.59"
    assert _stock(clients["sales"], 1) == 120


def test_cancelling_a_confirmed_order_returns_stock_and_keeps_the_frozen_rate(
    clients: dict[str, TestClient],
) -> None:
    order = _draft_with_line(clients["sales"])
    confirmed = clients["sales"].post(
        f"/api/orders/{order['id']}/confirm", headers={"If-Match": '"2"'}
    )
    assert confirmed.status_code == 200
    clients["admin"].patch("/api/settings", json={"tax_rate": "7"})

    response = clients["sales"].post(
        f"/api/orders/{order['id']}/cancel", headers={"If-Match": '"3"'}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "cancelled"
    assert body["tax_rate"] == confirmed.json()["tax_rate"]
    assert body["tax_rate"] != "7.00"
    assert (body["tax"], body["total"]) == (confirmed.json()["tax"], confirmed.json()["total"])
    assert _stock(clients["sales"], 1) == 120


def test_shipping_a_paid_order(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].post("/api/orders/4/ship")

    assert response.status_code == 200
    assert response.headers["etag"] == '"2"'
    assert response.json()["status"] == "shipped"

    assert_problem(
        clients["sales"].post("/api/orders/4/ship"),
        409,
        "INVALID_TRANSITION",
    )


@pytest.mark.parametrize(
    ("order_id", "action", "detail"),
    [
        (2, "confirm", "No se puede pasar el pedido de confirmado a confirmado."),
        (4, "cancel", "No se puede pasar el pedido de pagado a cancelado."),
        (1, "ship", "No se puede pasar el pedido de borrador a enviado."),
    ],
)
def test_invalid_transitions_use_spanish_labels(
    clients: dict[str, TestClient], order_id: int, action: str, detail: str
) -> None:
    response = clients["sales"].post(f"/api/orders/{order_id}/{action}")

    body = assert_problem(response, 409, "INVALID_TRANSITION")
    assert body["detail"] == detail


def test_double_submit_with_and_without_if_match(clients: dict[str, TestClient]) -> None:
    first = clients["sales"].post("/api/orders/1/confirm")
    assert first.status_code == 200

    assert_problem(clients["sales"].post("/api/orders/1/confirm"), 409, "INVALID_TRANSITION")
    assert_problem(
        clients["sales"].post("/api/orders/1/confirm", headers={"If-Match": '"1"'}),
        409,
        "VERSION_CONFLICT",
    )


def test_stale_if_match_is_a_conflict(clients: dict[str, TestClient]) -> None:
    assert_problem(
        clients["sales"].post("/api/orders/1/confirm", headers={"If-Match": '"2"'}),
        409,
        "VERSION_CONFLICT",
    )


def test_a_cancelled_draft_reads_the_same_totals_after_the_rate_changes(
    clients: dict[str, TestClient],
) -> None:
    order = _draft_with_line(clients["sales"])
    cancelled = clients["sales"].post(f"/api/orders/{order['id']}/cancel")
    assert cancelled.status_code == 200
    before = cancelled.json()

    clients["admin"].patch("/api/settings", json={"tax_rate": "7"})

    response = clients["sales"].get(f"/api/orders/{order['id']}")
    assert response.status_code == 200
    after = response.json()
    assert after["tax_rate"] == "10.00"
    assert after["subtotal"] == before["subtotal"]
    assert after["tax"] == before["tax"]
    assert after["total"] == before["total"]


def test_a_draft_uses_the_current_rate_and_a_confirmed_order_keeps_its_own(
    clients: dict[str, TestClient],
) -> None:
    order = _draft_with_line(clients["sales"])
    assert clients["sales"].get(f"/api/orders/{order['id']}").json()["tax_rate"] == "10.00"

    clients["admin"].patch("/api/settings", json={"tax_rate": "7"})
    draft = clients["sales"].get(f"/api/orders/{order['id']}").json()
    assert draft["tax_rate"] == "7.00"
    assert draft["tax"] == "2.79"
    assert draft["total"] == "42.59"

    confirmed = clients["sales"].post(
        f"/api/orders/{order['id']}/confirm", headers={"If-Match": '"2"'}
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["tax_rate"] == "7.00"

    clients["admin"].patch("/api/settings", json={"tax_rate": "5"})
    after = clients["sales"].get(f"/api/orders/{order['id']}").json()
    assert after["tax_rate"] == "7.00"
    assert after["tax"] == "2.79"
    assert after["total"] == "42.59"


@pytest.mark.parametrize("role", ["admin", "sales"])
def test_admin_and_sales_can_transition(clients: dict[str, TestClient], role: str) -> None:
    assert clients[role].post("/api/orders/1/cancel").status_code == 200


@pytest.mark.parametrize("role", ["finance", "readonly"])
def test_other_roles_cannot_transition(clients: dict[str, TestClient], role: str) -> None:
    for action in ("confirm", "cancel", "ship"):
        assert_problem(
            clients[role].post(f"/api/orders/1/{action}"),
            403,
            "FORBIDDEN",
        )


def test_a_stale_body_version_is_a_conflict(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].patch("/api/orders/1", json=change_customer_payload(1, 99))

    assert_problem(response, 409, "VERSION_CONFLICT")


def test_transitions_require_a_session(app: FastAPI) -> None:
    assert_problem(TestClient(app).post("/api/orders/1/confirm"), 401, "UNAUTHENTICATED")


def test_if_match_of_five_thousand_digits_is_a_validation_error(
    clients: dict[str, TestClient],
) -> None:
    response = clients["sales"].post("/api/orders/1/confirm", headers={"If-Match": "9" * 5000})

    assert_field_error(
        response,
        field="If-Match",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )
