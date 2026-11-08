"""Pure ASGI middleware for the test-only clock and fault controls."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

import psycopg
from sqlalchemy.exc import DBAPIError
from starlette._utils import get_route_path
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import Settings
from app.errors import (
    ERROR_MESSAGES,
    INTERNAL_ERROR,
    LOCK_TIMEOUT,
    get_request_id,
    problem_response,
)
from app.infra.clock import clock_offset
from app.infra.db import is_lock_timeout
from app.modules.testcontrols.controls import RequestControls

INJECTED_FAULT = "INJECTED_FAULT"
INJECTED_FAULT_DETAIL = "Falla inyectada para pruebas."
_MAX_LATENCY_MS = 10_000

logger = logging.getLogger(__name__)


def _sqlstate(error: BaseException) -> str | None:
    original = getattr(error, "orig", None)
    return getattr(original, "sqlstate", None) or getattr(error, "sqlstate", None)


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
        path = get_route_path(scope)
        if not path.startswith("/api/"):
            await self.app(scope, receive, send)
            return
        if method in ("GET", "HEAD") and path == "/api/health":
            await self.app(scope, receive, send)
            return

        try:
            if self.controls.uses_threadpool:
                offset, decision = await run_in_threadpool(
                    self.controls.load_request_controls,
                    method,
                    path,
                )
            else:
                offset, decision = self.controls.load_request_controls(method, path)
        except (DBAPIError, psycopg.Error) as error:
            await self._database_error(scope, receive, send, error)
            return

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

    async def _database_error(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        error: BaseException,
    ) -> None:
        """Render a database failure without letting the driver message escape."""
        request_id = get_request_id(Request(scope))
        sqlstate = _sqlstate(error) or "unknown"
        if is_lock_timeout(error):
            logger.warning(
                "Request controls lock timeout %s (SQLSTATE %s) on request %s",
                type(error).__name__,
                sqlstate,
                request_id,
            )
            response = problem_response(
                request_id,
                status=503,
                code=LOCK_TIMEOUT,
                detail=ERROR_MESSAGES[LOCK_TIMEOUT],
            )
        else:
            logger.error(
                "Request controls database error %s (SQLSTATE %s) on request %s",
                type(error).__name__,
                sqlstate,
                request_id,
            )
            response = problem_response(
                request_id,
                status=500,
                code=INTERNAL_ERROR,
                detail=ERROR_MESSAGES[INTERNAL_ERROR],
            )
        await response(scope, receive, send)
