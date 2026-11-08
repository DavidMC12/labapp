"""A full payment over HTTP against the PostgreSQL stores."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import Connection

from app.cli import seed_database
from app.config import Settings
from tests.integration.http_helpers import app_for, login_as_finance, settings_for
from tests.invoices.helpers import card_body


def test_a_full_card_payment_pays_the_invoice_over_http(
    db: Connection,
    database_settings: Settings,
) -> None:
    seed_database(database_settings)
    with app_for(settings_for(database_settings)) as app:
        with TestClient(app) as client:
            login_as_finance(client)

            response = client.post(
                "/api/invoices/1/payments",
                json=card_body(),
                headers={"Idempotency-Key": "http-payment-1"},
            )

            assert response.status_code == 201
            body = response.json()
            assert body["payment"]["status"] == "approved"
            assert body["invoice"]["status"] == "paid"
            assert body["invoice"]["version"] == 2

            reread = client.get("/api/invoices/1")
            assert reread.status_code == 200
            assert reread.json()["status"] == "paid"
            assert reread.json()["payments"][-1]["status"] == "approved"
