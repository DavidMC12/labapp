"""Tests for the cross-site request origin check."""

from __future__ import annotations

import pytest

from app.errors import ApiError
from app.security.origin import check_origin, cookie_secure

STATE_CHANGING_METHODS = ["POST", "PUT", "PATCH", "DELETE"]
APP_ORIGIN = "http://localhost:3000"


@pytest.mark.parametrize("method", STATE_CHANGING_METHODS)
def test_matching_origin_is_allowed(method: str) -> None:
    assert check_origin(method, APP_ORIGIN, APP_ORIGIN) is None


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "https://localhost:3000",
        "https://evil.test",
    ],
)
@pytest.mark.parametrize("method", STATE_CHANGING_METHODS)
def test_different_origin_is_rejected(method: str, origin: str) -> None:
    with pytest.raises(ApiError) as error:
        check_origin(method, origin, APP_ORIGIN)

    assert error.value.status == 403
    assert error.value.code == "CSRF_ORIGIN_MISMATCH"
    assert error.value.detail == "La solicitud no proviene de la aplicación."


@pytest.mark.parametrize(
    ("origin", "app_origin"),
    [
        ("http://localhost:3000", "http://localhost:3000/"),
        ("http://localhost:3000/", "http://localhost:3000"),
        ("http://localhost:3000/", "http://localhost:3000/"),
    ],
)
@pytest.mark.parametrize("method", STATE_CHANGING_METHODS)
def test_trailing_slash_is_ignored(method: str, origin: str, app_origin: str) -> None:
    assert check_origin(method, origin, app_origin) is None


@pytest.mark.parametrize("method", STATE_CHANGING_METHODS)
def test_missing_origin_is_allowed(method: str) -> None:
    assert check_origin(method, None, APP_ORIGIN) is None


@pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS", "TRACE"])
def test_safe_methods_are_never_checked(method: str) -> None:
    assert check_origin(method, "https://evil.test", APP_ORIGIN) is None


def test_host_is_compared_case_insensitively() -> None:
    assert check_origin("POST", "http://LOCALHOST:3000", APP_ORIGIN) is None


@pytest.mark.parametrize("origin", ["not-a-url", "http://localhost:notaport"])
def test_malformed_origin_is_rejected(origin: str) -> None:
    with pytest.raises(ApiError) as error:
        check_origin("POST", origin, APP_ORIGIN)

    assert error.value.code == "CSRF_ORIGIN_MISMATCH"


@pytest.mark.parametrize(
    ("app_origin", "expected"),
    [
        ("https://app.test", True),
        ("https://app.test:8443", True),
        ("http://app.test", False),
        ("", False),
    ],
)
def test_cookie_secure(app_origin: str, expected: bool) -> None:
    assert cookie_secure(app_origin) is expected
