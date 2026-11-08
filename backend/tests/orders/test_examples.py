"""The literal examples of the Orders API subsection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.config import Settings
from app.infra.clock import OffsetClock
from app.main import create_app
from app.modules.auth.seed import DEMO_PASSWORD
from app.openapi_examples import (
    ORDER_CREATE_REQUEST,
    ORDER_LINE_CREATE_REQUEST,
    ORDER_LINE_CREATED_201,
    VALIDATION_ERROR_422,
)
from tests.infra.helpers import FixedClock


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
    created = client.post("/api/orders", json=ORDER_CREATE_REQUEST)
    assert created.status_code == 201

    clock.advance(timedelta(minutes=1))
    response = client.post(
        "/api/orders/8/lines",
        json=ORDER_LINE_CREATE_REQUEST,
    )

    assert response.status_code == 201
    assert response.headers["etag"] == '"2"'
    assert response.json() == ORDER_LINE_CREATED_201


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
    assert client.post("/api/orders", json=ORDER_CREATE_REQUEST).status_code == 201
    clock.advance(timedelta(minutes=1))
    assert (
        client.post(
            "/api/orders/8/lines",
            json=ORDER_LINE_CREATE_REQUEST,
        ).status_code
        == 201
    )

    response = client.post(
        "/api/orders/8/lines",
        json={**ORDER_LINE_CREATE_REQUEST, "quantity": 1000, "version": 2},
    )

    assert response.status_code == 422
    assert response.json() == VALIDATION_ERROR_422
