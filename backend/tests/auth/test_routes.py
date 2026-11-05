"""Tests for the authentication routes."""

from __future__ import annotations

from datetime import timedelta
from http.cookies import Morsel, SimpleCookie
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.auth.constants import SESSION_COOKIE_NAME
from app.modules.auth.routes import LoginRequest
from app.modules.auth.seed import DEMO_PASSWORD

LOGIN = "/api/auth/login"
LOGOUT = "/api/auth/logout"
ME = "/api/auth/me"
ADMIN = {
    "id": 1,
    "name": "Admin Demo",
    "email": "admin@labapp.test",
    "role": "admin",
}


def _login(
    client: TestClient,
    email: str = "admin@labapp.test",
    password: str = DEMO_PASSWORD,
) -> Any:
    return client.post(LOGIN, json={"email": email, "password": password})


def _cookie(response: Any) -> Morsel[str]:
    cookie: SimpleCookie[str] = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    return cookie[SESSION_COOKIE_NAME]


def test_login_returns_the_user_and_a_session_cookie(client: TestClient) -> None:
    response = _login(client)

    assert response.status_code == 200
    assert response.json() == ADMIN
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]

    morsel = _cookie(response)
    assert morsel.value
    assert bool(morsel["httponly"]) is True
    assert morsel["path"] == "/"
    assert morsel["samesite"].lower() == "lax"
    assert bool(morsel["secure"]) is False
    assert bool(morsel["max-age"]) is False
    assert bool(morsel["expires"]) is False
    assert bool(morsel["domain"]) is False


def test_login_sets_a_secure_cookie_for_an_https_origin(
    make_app: Any,
) -> None:
    app: FastAPI = make_app(app_origin="https://app.test")
    client = TestClient(app)

    response = _login(client)

    assert response.status_code == 200
    assert bool(_cookie(response)["secure"]) is True


def test_logout_sets_a_secure_cookie_for_an_https_origin(
    make_app: Any,
) -> None:
    app: FastAPI = make_app(app_origin="https://app.test")
    client = TestClient(app)

    response = client.post(LOGOUT)

    assert response.status_code == 204
    assert bool(_cookie(response)["secure"]) is True


def test_me_with_a_session_returns_the_user(client: TestClient) -> None:
    _login(client)

    response = client.get(ME)

    assert response.status_code == 200
    assert response.json() == ADMIN
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]


def test_me_without_a_session_is_unauthenticated(client: TestClient) -> None:
    response = client.get(ME)

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["x-request-id"]
    body = response.json()
    assert body["status"] == 401
    assert body["code"] == "UNAUTHENTICATED"
    assert body["detail"] == "Inicia sesión para continuar."


def test_me_expires_with_the_application_clock(client: TestClient, app: FastAPI) -> None:
    _login(client)
    app.state.container.clock.advance(timedelta(hours=8))

    response = client.get(ME)

    assert response.status_code == 401
    assert response.json()["code"] == "SESSION_EXPIRED"


def test_logout_ends_the_session_and_expires_the_cookie(client: TestClient) -> None:
    _login(client)

    response = client.post(LOGOUT)

    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["x-request-id"]
    morsel = _cookie(response)
    assert morsel["max-age"] == "0"
    assert morsel["path"] == "/"
    assert bool(morsel["httponly"]) is True
    assert morsel["samesite"].lower() == "lax"
    assert bool(morsel["domain"]) is False
    assert bool(morsel["secure"]) is False
    assert client.get(ME).status_code == 401


def test_logout_without_a_session_is_still_204(client: TestClient) -> None:
    response = client.post(LOGOUT)

    assert response.status_code == 204
    assert _cookie(response)["max-age"] == "0"


def test_logout_with_an_unknown_cookie_is_still_204(client: TestClient) -> None:
    response = client.post(
        LOGOUT,
        headers={"Cookie": f"{SESSION_COOKIE_NAME}=unknown-token"},
    )

    assert response.status_code == 204
    assert _cookie(response)["max-age"] == "0"


def test_login_missing_password_is_required(client: TestClient) -> None:
    response = client.post(LOGIN, json={"email": "admin@labapp.test"})

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["x-request-id"]
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["detail"] == "Revisa los datos ingresados."
    assert body["errors"] == [
        {
            "field": "password",
            "code": "REQUIRED",
            "message": "Este campo es obligatorio.",
        }
    ]


def test_login_wrong_password_is_invalid_credentials(client: TestClient) -> None:
    response = _login(client, password="wrong-password")

    assert response.status_code == 401
    assert "set-cookie" not in response.headers
    body = response.json()
    assert body["code"] == "INVALID_CREDENTIALS"
    assert body["detail"] == "Email o contraseña incorrectos."


def test_login_unknown_email_is_invalid_credentials(client: TestClient) -> None:
    response = _login(client, email="nobody@labapp.test")

    assert response.status_code == 401
    assert "set-cookie" not in response.headers
    body = response.json()
    assert body["code"] == "INVALID_CREDENTIALS"
    assert body["detail"] == "Email o contraseña incorrectos."


def test_repeated_login_revokes_the_previous_session(
    client: TestClient,
    app: FastAPI,
) -> None:
    _login(client)
    _login(client)

    assert len(app.state.container.sessions.snapshot()) == 1


def test_openapi_documents_the_auth_contract(client: TestClient) -> None:
    document = client.get("/openapi.json").json()

    assert "UserOut" in document["components"]["schemas"]
    assert "401" in document["paths"][LOGIN]["post"]["responses"]
    assert "401" in document["paths"][ME]["get"]["responses"]


def test_login_request_repr_hides_the_email_and_password() -> None:
    rendered = repr(LoginRequest(email="admin@labapp.test", password="super-secret"))

    assert "admin@labapp.test" not in rendered
    assert "super-secret" not in rendered


def test_container_repr_hides_the_settings(app: FastAPI) -> None:
    container = app.state.container
    rendered = repr(container)

    assert container.settings.session_secret not in rendered
    assert container.settings.database_url not in rendered
