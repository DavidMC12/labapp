"""Authentication routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, Field

from app.domain.permissions import Role
from app.modules.auth.constants import SESSION_COOKIE_NAME
from app.modules.auth.container import Container
from app.modules.auth.dependencies import (
    get_container,
    get_current_user,
    session_cookie_values,
)
from app.modules.auth.models import User
from app.openapi import documented_responses
from app.security.origin import cookie_secure

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """The login payload."""

    email: str = Field(repr=False)
    password: str = Field(repr=False)


class UserOut(BaseModel):
    """The public user representation."""

    id: int
    name: str
    email: str
    role: Role


def _user_out(user: User) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email, role=user.role)


@router.post(
    "/login",
    response_model=UserOut,
    responses=documented_responses(
        method="POST",
        protected=False,
        body=True,
        unavailable=("SERVICE_BUSY", "LOCK_TIMEOUT"),
        extra={
            401: "The email or the password is wrong. Code: `INVALID_CREDENTIALS`.",
            422: "The body is invalid. Code: `VALIDATION_ERROR` (with `errors[]`).",
        },
    ),
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    container: Annotated[Container, Depends(get_container)],
) -> UserOut:
    """Verify credentials and start a session."""
    user, token = container.auth.login(
        payload.email,
        payload.password,
        presented_tokens=session_cookie_values(request),
    )
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        path="/",
        httponly=True,
        samesite="Lax",
        secure=cookie_secure(container.settings.app_origin),
    )
    response.headers["Cache-Control"] = "no-store"
    return _user_out(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=documented_responses(method="POST", protected=False),
)
def logout(
    request: Request,
    container: Annotated[Container, Depends(get_container)],
) -> Response:
    """End the current session, if any."""
    for token in session_cookie_values(request):
        container.auth.logout(token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="Lax",
        secure=cookie_secure(container.settings.app_origin),
    )
    return response


@router.get(
    "/me",
    response_model=UserOut,
    responses=documented_responses(method="GET"),
)
def me(
    user: Annotated[User, Depends(get_current_user)],
    response: Response,
) -> UserOut:
    """Return the user of the current session."""
    response.headers["Cache-Control"] = "no-store"
    return _user_out(user)
