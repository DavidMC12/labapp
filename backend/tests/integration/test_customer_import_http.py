"""The customer import over HTTP against the PostgreSQL stores (task 058)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import Connection

from app.cli import seed_database
from app.config import Settings
from app.modules.auth.seed import DEMO_PASSWORD
from tests.integration.http_helpers import app_for, settings_for


def _login(client: TestClient, email: str = "sales@labapp.test") -> None:
    assert (
        client.post("/api/auth/login", json={"email": email, "password": DEMO_PASSWORD}).status_code
        == 200
    )


def _upload(client: TestClient, text: str, name: str = "c.csv"):
    return client.post("/api/customers/import", files={"file": (name, text.encode(), "text/csv")})


def test_the_csv_import_works_end_to_end_over_http_on_postgres(
    db: Connection, database_settings: Settings
) -> None:
    seed_database(database_settings)
    with app_for(settings_for(database_settings)) as app:
        with TestClient(app) as client:
            _login(client)
            good = (
                "name,email,phone\r\nImp Uno,UNO@x.test,+57 300 1112233\r\nImp Dos,dos@x.test,\r\n"
            )
            r = _upload(client, good)
            assert r.status_code == 201, r.text
            body = r.json()
            assert body["created"] == 2 and [i["id"] for i in body["items"]] == [11, 12]
            assert body["items"][0]["email"] == "uno@x.test" and body["items"][1]["phone"] is None
            # visible in the list, searchable (the search columns were filled), exported
            assert client.get("/api/customers").json()["total"] == 12
            assert client.get("/api/customers?q=imp%20dos").json()["total"] == 1
            assert client.get("/api/customers?q=UNO@X.test").json()["total"] == 1
            # an email that exists (any case) and a repeated one: nothing is created
            bad = "name,email\r\nOtro Uno,uno@X.TEST\r\nOtro Dos,nuevo@x.test\r\nOtro Tres,nuevo@x.test\r\n"
            r = _upload(client, bad)
            assert r.status_code == 422, r.text
            fields = [(e["field"], e["code"]) for e in r.json()["errors"]]
            assert ("rows[2].email", "CUSTOMER_EMAIL_TAKEN") in fields and (
                "rows[4].email",
                "CUSTOMER_EMAIL_TAKEN",
            ) in fields, fields
            assert client.get("/api/customers").json()["total"] == 12
            # the sequence kept going: the next customer is 13
            r = client.post("/api/customers", json={"name": "Normal Uno", "email": "n1@x.test"})
            assert r.status_code == 201 and r.json()["id"] == 13, r.text
            # a 200-row file in one transaction
            big = "name,email\r\n" + "".join(f"Fila {i:03d},big{i}@x.test\r\n" for i in range(200))
            r = _upload(client, big)
            assert r.status_code == 201 and r.json()["created"] == 200
            assert client.get("/api/customers").json()["total"] == 213
            # permissions on the real stack
            _login(client, "finance@labapp.test")
            assert _upload(client, good).status_code == 403
            export = client.get("/api/customers/export")
            assert export.status_code == 200 and export.text.count("\r\n") == 214
