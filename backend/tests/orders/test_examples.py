"""The literal examples of the Orders API subsection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.config import Settings
from app.infra.clock import OffsetClock
from app.main import create_app
from app.modules.auth.seed import DEMO_PASSWORD
from tests.infra.helpers import FixedClock

EXAMPLE = {
    "id": 8,
    "number": "PED-0008",
    "status": "draft",
    "customer": {"id": 1, "name": "Acme Industrial S.A.", "status": "active"},
    "lines": [
        {
            "id": 10,
            "product_id": 1,
            "sku": "KB-100",
            "name": "Teclado USB",
            "quantity": 2,
            "unit_price": "19.90",
            "line_total": "39.80",
        }
    ],
    "subtotal": "39.80",
    "tax_rate": "10.00",
    "tax": "3.98",
    "total": "43.78",
    "invoice_id": None,
    "version": 2,
    "created_at": "2026-11-05T15:00:00Z",
    "updated_at": "2026-11-05T15:01:00Z",
}


def test_the_documented_line_response_is_reproduced_literally() -> None:
    clock = OffsetClock(FixedClock(datetime(2026, 11, 5, 15, 0, tzinfo=UTC)))
    app = create_app(
        Settings(
            session_secret="test-secret",
            test_mode=False,
            app_origin="http://localhost:3000",
        ),
        clock=clock,
    )
    client = TestClient(app)
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "sales@labapp.test", "password": DEMO_PASSWORD},
        ).status_code
        == 200
    )
    created = client.post("/api/orders", json={"customer_id": 1})
    assert created.status_code == 201

    clock.advance(timedelta(minutes=1))
    response = client.post(
        "/api/orders/8/lines",
        json={"product_id": 1, "quantity": 2, "version": 1},
    )

    assert response.status_code == 201
    assert response.headers["etag"] == '"2"'
    assert response.json() == EXAMPLE


def test_the_documented_quantity_error_is_reproduced_literally() -> None:
    clock = OffsetClock(FixedClock(datetime(2026, 11, 5, 15, 0, tzinfo=UTC)))
    app = create_app(
        Settings(
            session_secret="test-secret",
            test_mode=False,
            app_origin="http://localhost:3000",
        ),
        clock=clock,
    )
    client = TestClient(app)
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "sales@labapp.test", "password": DEMO_PASSWORD},
        ).status_code
        == 200
    )
    assert client.post("/api/orders", json={"customer_id": 1}).status_code == 201
    clock.advance(timedelta(minutes=1))
    assert (
        client.post(
            "/api/orders/8/lines",
            json={"product_id": 1, "quantity": 2, "version": 1},
        ).status_code
        == 201
    )

    response = client.post(
        "/api/orders/8/lines",
        json={"product_id": 1, "quantity": 1000, "version": 2},
    )

    assert response.status_code == 422
    assert response.json() == {
        "type": "about:blank",
        "title": "Unprocessable Content",
        "status": 422,
        "code": "VALIDATION_ERROR",
        "detail": "Revisa los datos ingresados.",
        "errors": [
            {
                "field": "quantity",
                "code": "OUT_OF_RANGE",
                "message": "El valor debe estar entre 1 y 999.",
            }
        ],
    }
