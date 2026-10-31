"""Tests for the test-controls guard and rate-limiting switch."""

from __future__ import annotations

import pytest

from app.security.test_guard import (
    has_valid_test_token,
    rate_limiting_enabled,
)
from app.security.test_guard import (
    test_controls_allowed as controls_allowed,
)

GUARD_CASES = [
    # test_mode, token, header, controls allowed, rate limiting enabled
    (True, "", None, True, False),
    (True, "", "", True, False),
    (True, "", "anything", True, False),
    (True, "", "secret", True, False),
    (True, "secret", None, True, False),
    (True, "secret", "wrong", True, False),
    (True, "secret", "secret", True, False),
    (False, "", None, False, True),
    (False, "", "", False, True),
    (False, "", "anything", False, True),
    (False, "", "secret", False, True),
    (False, "secret", None, False, True),
    (False, "secret", "wrong", False, True),
    (False, "secret", "secret", True, False),
]


@pytest.mark.parametrize(
    ("test_mode", "test_token", "header", "controls_allowed_result", "limiting_enabled"),
    GUARD_CASES,
)
def test_guard_table(
    test_mode: bool,
    test_token: str,
    header: str | None,
    controls_allowed_result: bool,
    limiting_enabled: bool,
) -> None:
    assert controls_allowed(test_mode, test_token, header) is controls_allowed_result
    assert rate_limiting_enabled(test_mode, test_token, header) is limiting_enabled


@pytest.mark.parametrize("header", [None, "", "anything"])
def test_empty_token_never_matches(header: str | None) -> None:
    assert has_valid_test_token("", header) is False


@pytest.mark.parametrize("header", [None, "", "wrong", "secre", "secret ", "Secret"])
def test_wrong_token_never_matches(header: str | None) -> None:
    assert has_valid_test_token("secret", header) is False


def test_exact_token_matches() -> None:
    assert has_valid_test_token("secret", "secret") is True


def test_non_ascii_token_is_compared_safely() -> None:
    assert has_valid_test_token("sëcret", "sëcret") is True
    assert has_valid_test_token("sëcret", "secret") is False
