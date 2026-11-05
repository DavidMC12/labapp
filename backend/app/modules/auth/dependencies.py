"""FastAPI dependencies for the authentication module."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request

from app.domain.permissions import Action, require
from app.modules.auth.constants import SESSION_COOKIE_NAME
from app.modules.auth.container import Container
from app.modules.auth.models import User


def get_container(request: Request) -> Container:
    """Return the container built by create_app."""
    return request.app.state.container


def session_cookie_values(request: Request) -> list[str]:
    """Return every labapp_session value from the raw Cookie header(s)."""
    values: list[str] = []
    for header in request.headers.getlist("cookie"):
        for part in header.split(";"):
            name, separator, value = part.strip().partition("=")
            if separator and name == SESSION_COOKIE_NAME and value:
                values.append(value)
    return values


def get_current_user(
    request: Request,
    container: Annotated[Container, Depends(get_container)],
) -> User:
    """Authenticate the session cookie and return its user."""
    return container.auth.authenticate(request.cookies.get(SESSION_COOKIE_NAME))


def require_action(action: Action) -> Callable[..., User]:
    """Build a dependency that enforces one permission action."""

    def dependency(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        require(user.role, action)
        return user

    return dependency
