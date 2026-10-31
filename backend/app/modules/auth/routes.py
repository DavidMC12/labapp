"""Authentication routes."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel

from app.domain.permissions import Role
from app.modules.auth.constants import SESSION_COOKIE_NAME
from app.modules.auth.container import Container
from app.modules.auth.dependencies import get_container, get_current_user
from app.modules.auth.models import User
from app.security.origin import cookie_secure

router = APIRouter(prefix="/api/auth", tags=["auth"])

_PROBLEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["type", "title", "status", "code", "detail"],
    "properties": {
        "type": {"type": "string"},
        "title": {"type": "string"},
        "status": {"type": "integer"},
        "code": {"type": "string"},
        "detail": {"type": "string"},
    },
}

_UNAUTHORIZED_RESPONSE: dict[str, Any] = {
    "description": "Authentication failed.",
    "content": {"application/problem+json": {"schema": _PROBLEM_SCHEMA}},
}


class LoginRequest(BaseModel):
    """The login payload."""

    email: str
    password: str


class UserOut(BaseModel):
    """The public user representation."""

    id: int
    name: str
    email: str
    role: Role


def _user_out(user: User) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email, role=user.role)


@router.post("/login", response_model=UserOut, responses={401: _UNAUTHORIZED_RESPONSE})
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
        request.cookies.get(SESSION_COOKIE_NAME),
    )
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        path="/",
        httponly=True,
        samesite="lax",
        secure=cookie_secure(container.settings.app_origin),
    )
    response.headers["Cache-Control"] = "no-store"
    return _user_out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def logout(
    request: Request,
    container: Annotated[Container, Depends(get_container)],
) -> Response:
    """End the current session, if any."""
    container.auth.logout(request.cookies.get(SESSION_COOKIE_NAME))
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=cookie_secure(container.settings.app_origin),
    )
    return response


@router.get("/me", response_model=UserOut, responses={401: _UNAUTHORIZED_RESPONSE})
def me(
    user: Annotated[User, Depends(get_current_user)],
    response: Response,
) -> UserOut:
    """Return the user of the current session."""
    response.headers["Cache-Control"] = "no-store"
    return _user_out(user)
