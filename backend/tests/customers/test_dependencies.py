"""Tests for the customer dependency helpers."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from starlette.requests import Request

from app.modules.customers.dependencies import get_repository


def test_get_repository_returns_the_repository_of_the_application(app: FastAPI) -> None:
    scope: dict[str, Any] = {
        "type": "http",
        "app": app,
        "method": "GET",
        "path": "/api/customers",
        "headers": [],
        "query_string": b"",
    }

    assert get_repository(Request(scope)) is app.state.customer_repository
