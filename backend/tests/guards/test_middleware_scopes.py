"""Direct ASGI tests for the request id and body size middlewares."""

from __future__ import annotations

import asyncio
from typing import Any

from app.middleware import BodySizeLimitMiddleware, RequestIdMiddleware


async def _noop_receive() -> dict[str, Any]:
    return {"type": "http.request", "body": b"", "more_body": False}


async def _noop_send(message: dict[str, Any]) -> None:
    return None


def test_the_request_id_middleware_passes_a_lifespan_scope_through() -> None:
    scopes: list[dict[str, Any]] = []

    async def inner(scope: dict[str, Any], receive: Any, send: Any) -> None:
        scopes.append(scope)

    scope: dict[str, Any] = {"type": "lifespan"}

    asyncio.run(RequestIdMiddleware(inner)(scope, _noop_receive, _noop_send))

    assert scopes == [scope]
    assert "state" not in scope


def test_the_body_size_middleware_passes_a_lifespan_scope_through() -> None:
    scopes: list[dict[str, Any]] = []

    async def inner(scope: dict[str, Any], receive: Any, send: Any) -> None:
        scopes.append(scope)

    scope: dict[str, Any] = {"type": "lifespan"}

    asyncio.run(BodySizeLimitMiddleware(inner)(scope, _noop_receive, _noop_send))

    assert scopes == [scope]


def test_a_malformed_content_length_counts_as_zero() -> None:
    scopes: list[dict[str, Any]] = []

    async def inner(scope: dict[str, Any], receive: Any, send: Any) -> None:
        scopes.append(scope)

    scope: dict[str, Any] = {
        "type": "http",
        "headers": [(b"content-length", b"not-a-number")],
        "method": "POST",
        "path": "/api/auth/login",
        "state": {},
    }

    asyncio.run(BodySizeLimitMiddleware(inner)(scope, _noop_receive, _noop_send))

    assert scopes == [scope]


def test_the_limited_receive_returns_a_non_request_message_unchanged() -> None:
    messages: list[dict[str, Any]] = []

    async def inner(scope: dict[str, Any], receive: Any, send: Any) -> None:
        messages.append(await receive())

    async def disconnect() -> dict[str, Any]:
        return {"type": "http.disconnect"}

    scope: dict[str, Any] = {
        "type": "http",
        "headers": [],
        "method": "GET",
        "path": "/api/health",
        "state": {},
    }

    asyncio.run(BodySizeLimitMiddleware(inner)(scope, disconnect, _noop_send))

    assert messages == [{"type": "http.disconnect"}]
