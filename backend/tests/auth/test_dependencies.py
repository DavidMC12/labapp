"""Tests for the current-user and permission dependencies."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.domain.permissions import Action
from app.modules.auth.dependencies import require_action
from app.modules.auth.models import User
from app.modules.auth.seed import DEMO_PASSWORD

ROLES = [
    ("admin@labapp.test", 1, True),
    ("sales@labapp.test", 2, False),
    ("finance@labapp.test", 3, False),
    ("readonly@labapp.test", 4, False),
]


def _add_protected_routes(app: FastAPI) -> FastAPI:
    @app.get("/api/test/view")
    def view(user: Annotated[User, Depends(require_action(Action.VIEW))]) -> dict[str, int]:
        return {"id": user.id}

    @app.get("/api/test/tax-rate")
    def tax_rate(
        user: Annotated[User, Depends(require_action(Action.CHANGE_TAX_RATE))],
    ) -> dict[str, int]:
        return {"id": user.id}

    return app


def test_permission_dependency_for_every_role(
    make_app: Callable[..., FastAPI],
) -> None:
    app = _add_protected_routes(make_app())

    for email, user_id, may_change_tax_rate in ROLES:
        client = TestClient(app)
        login = client.post(
            "/api/auth/login",
            json={"email": email, "password": DEMO_PASSWORD},
        )
        assert login.status_code == 200

        view = client.get("/api/test/view")
        assert view.status_code == 200
        assert view.json() == {"id": user_id}

        tax_rate = client.get("/api/test/tax-rate")
        if may_change_tax_rate:
            assert tax_rate.status_code == 200
            assert tax_rate.json() == {"id": user_id}
        else:
            assert tax_rate.status_code == 403
            body = tax_rate.json()
            assert body["code"] == "FORBIDDEN"
            assert body["detail"] == "No tienes permiso para realizar esta acción."


def test_protected_routes_need_a_session(make_app: Callable[..., FastAPI]) -> None:
    app = _add_protected_routes(make_app())
    client = TestClient(app)

    response = client.get("/api/test/view")

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"
