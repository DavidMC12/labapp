"""Guard the test-only controls before routing or body handling."""

from __future__ import annotations

from uuid import uuid4

from starlette._utils import get_route_path
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import Settings
from app.errors import ERROR_MESSAGES, NOT_FOUND, get_request_id, problem_response
from app.security.controls_guard import controls_allowed


def _is_test_path(path: str) -> bool:
    return path == "/__test__" or path.startswith("/__test__/")


def _request_id(scope: Scope) -> str:
    """Return the request id of an HTTP request or a fresh one for a websocket."""
    if scope["type"] == "http":
        return get_request_id(Request(scope))
    state = scope.get("state") or {}
    request_id = state.get("request_id")
    return request_id if isinstance(request_id, str) and request_id else str(uuid4())


class ControlsGuardMiddleware:
    """Answer 404 to unauthenticated probes of the test controls."""

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path = get_route_path(scope)
        if _is_test_path(path):
            headers = Headers(scope=scope)
            allowed = controls_allowed(
                self.settings.test_mode,
                self.settings.test_token,
                headers.get("x-test-token"),
            )
            if not allowed:
                response = problem_response(
                    _request_id(scope),
                    status=404,
                    code=NOT_FOUND,
                    detail=ERROR_MESSAGES[NOT_FOUND],
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)
