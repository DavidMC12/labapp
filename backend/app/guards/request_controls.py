"""Pure ASGI middleware for the test-only clock and fault controls."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import Settings
from app.errors import get_request_id, problem_response
from app.infra.clock import clock_offset
from app.modules.testcontrols.controls import RequestControls

INJECTED_FAULT = "INJECTED_FAULT"
INJECTED_FAULT_DETAIL = "Falla inyectada para pruebas."
_MAX_LATENCY_MS = 10_000


def _is_test_path(path: str) -> bool:
    return path == "/__test__" or path.startswith("/__test__/")


class RequestControlsMiddleware:
    """Apply the stored clock offset and consume one fault per request.

    It runs only when the controls are enabled. The load is one threadpool call and
    one database transaction in PostgreSQL mode; the context value is set afterwards
    in this coroutine because the worker thread has a copy of the context.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        settings: Settings,
        controls: RequestControls,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.app = app
        self.controls = controls
        self.enabled = settings.test_mode or bool(settings.test_token)
        self.sleep = sleep

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.enabled:
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        path = scope.get("path", "")
        if _is_test_path(path) or (method == "GET" and path == "/api/health"):
            await self.app(scope, receive, send)
            return

        if self.controls.uses_threadpool:
            offset, decision = await run_in_threadpool(
                self.controls.load_request_controls,
                method,
                path,
            )
        else:
            offset, decision = self.controls.load_request_controls(method, path)

        token = clock_offset.set(offset)
        try:
            if decision is not None:
                await self.sleep(min(decision.latency_ms, _MAX_LATENCY_MS) / 1000)
                if decision.status is not None:
                    response = problem_response(
                        get_request_id(Request(scope)),
                        status=decision.status,
                        code=INJECTED_FAULT,
                        detail=INJECTED_FAULT_DETAIL,
                    )
                    await response(scope, receive, send)
                    return

            await self.app(scope, receive, send)
        finally:
            clock_offset.reset(token)
