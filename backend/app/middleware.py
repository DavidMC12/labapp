from __future__ import annotations

import re
from uuid import uuid4

from starlette._utils import get_route_path
from starlette.datastructures import Headers, MutableHeaders
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.errors import (
    ERROR_MESSAGES,
    PAYLOAD_TOO_LARGE,
    REQUEST_ID_HEADER,
    get_request_id,
    problem_response,
)

MAX_BODY_BYTES = 100 * 1024
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class RequestIdMiddleware:
    """Attach a request id to every HTTP response and to the request state."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming_request_id = Headers(scope=scope).get(REQUEST_ID_HEADER)
        if incoming_request_id is not None and REQUEST_ID_PATTERN.fullmatch(incoming_request_id):
            request_id = incoming_request_id
        else:
            request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        await self.app(scope, receive, send_with_request_id)


class BodySizeLimitMiddleware:
    """Reject requests whose declared or streamed body exceeds the limit.

    A declared ``Content-Length`` above the limit is rejected before reading the
    body. A chunked body is rejected from the wrapped ``receive`` as soon as the
    bytes received exceed the limit.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = Headers(scope=scope).get("content-length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                declared_size = 0
            if declared_size > MAX_BODY_BYTES:
                response = problem_response(
                    get_request_id(Request(scope)),
                    status=413,
                    code=PAYLOAD_TOO_LARGE,
                    detail=ERROR_MESSAGES[PAYLOAD_TOO_LARGE],
                )
                await response(scope, receive, send)
                return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > MAX_BODY_BYTES:
                    raise HTTPException(status_code=413)
            return message

        await self.app(scope, limited_receive, send)


API_PATH_PREFIX = "/api/"
TEST_CONTROLS_PATH_PREFIX = "/__test__/"
CACHEABLE_PATHS = frozenset({"/api/openapi.json", "/api/docs"})


class ApiResponseHeadersMiddleware:
    """Add the security headers that every API answer carries (SPEC section 8).

    The API answers depend on the session or on the data, so a shared cache or a
    browser must never keep them. The contract and its Swagger page are the only
    exception: they are public documents and only need ``nosniff``.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = get_route_path(scope)
        if not (path.startswith(API_PATH_PREFIX) or path.startswith(TEST_CONTROLS_PATH_PREFIX)):
            await self.app(scope, receive, send)
            return

        only_nosniff = scope.get("method") == "GET" and path in CACHEABLE_PATHS

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                if not only_nosniff and "cache-control" not in headers:
                    headers["Cache-Control"] = "no-store"
            await send(message)

        await self.app(scope, receive, send_with_headers)
