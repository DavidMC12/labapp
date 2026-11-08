"""A lock timeout must not consume the Idempotency-Key of the payment."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, select

from app.cli import seed_database
from app.config import Settings
from app.modules.invoices.tables import invoices
from tests.integration.http_helpers import app_for, login_as_finance, settings_for
from tests.invoices.helpers import card_body

LOCK_TIMEOUT_MS = 250


def test_a_lock_timeout_leaves_the_idempotency_key_free(
    db: Connection,
    database_settings: Settings,
    database_engine: Engine,
) -> None:
    seed_database(database_settings)
    settings = settings_for(database_settings, lock_timeout_ms=LOCK_TIMEOUT_MS)
    with app_for(settings) as app:
        with TestClient(app) as client:
            login_as_finance(client)

            with database_engine.connect() as holder:
                holder.execute(select(invoices.c.id).where(invoices.c.id == 1).with_for_update())
                blocked = client.post(
                    "/api/invoices/1/payments",
                    json=card_body(),
                    headers={"Idempotency-Key": "retry-key"},
                )
                assert blocked.status_code == 503
                assert blocked.json()["code"] == "LOCK_TIMEOUT"
                holder.rollback()

            paid = client.post(
                "/api/invoices/1/payments",
                json=card_body(),
                headers={"Idempotency-Key": "retry-key"},
            )

            assert paid.status_code == 201
            assert paid.json()["invoice"]["status"] == "paid"
