"""Best-effort rate limits for the API and the test controls."""

from __future__ import annotations

from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.errors import get_request_id, problem_response
from app.modules.auth.container import Container
from app.security.client_ip import client_ip
from app.security.controls_guard import rate_limiting_enabled
from app.security.ratelimit import rate_limited_error


def _is_test_path(path: str) -> bool:
    return path == "/__test__" or path.startswith("/__test__/")


def _is_limited_path(path: str, method: str) -> bool:
    if method == "GET" and path == "/api/health":
        return False
    return path.startswith("/api/") or _is_test_path(path)


class RateLimitMiddleware:
    """Count requests per client IP and answer 429 when a window is full."""

    def __init__(self, app: ASGIApp, container: Container) -> None:
        self.app = app
        self.container = container

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "")
        if not _is_limited_path(path, method):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        if not rate_limiting_enabled(
            self.container.settings.test_mode,
            self.container.settings.test_token,
            headers.get("x-test-token"),
        ):
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        peer = client[0] if client else "unknown"
        forwarded_for = ",".join(headers.getlist("x-forwarded-for")) or None
        key = client_ip(
            peer,
            forwarded_for,
            self.container.settings.trusted_proxy_count,
        )

        decision = self.container.limiters.general.hit(key)
        if not decision.allowed:
            await self._reject(scope, receive, send, decision.retry_after)
            return

        if method == "POST" and path == "/api/auth/login":
            decision = self.container.limiters.login.hit(key)
            if not decision.allowed:
                await self._reject(scope, receive, send, decision.retry_after)
                return

        await self.app(scope, receive, send)

    async def _reject(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        retry_after: int,
    ) -> None:
        error = rate_limited_error(retry_after)
        response = problem_response(
            get_request_id(Request(scope)),
            status=error.status,
            code=error.code,
            detail=error.detail,
            title=error.title,
            extra=error.extra,
            headers={"Retry-After": str(retry_after)},
        )
        await response(scope, receive, send)
