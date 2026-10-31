"""Guards for the test-only controls and rate limiting."""

from __future__ import annotations

import hmac


def has_valid_test_token(test_token: str, header: str | None) -> bool:
    """Return whether a non-empty configured token matches the header."""
    if not test_token or header is None:
        return False
    return hmac.compare_digest(test_token.encode("utf-8"), header.encode("utf-8"))


def controls_allowed(test_mode: bool, test_token: str, header: str | None) -> bool:
    """Implement the test-controls guard table from the architecture."""
    if test_mode:
        return True
    return has_valid_test_token(test_token, header)


def rate_limiting_enabled(test_mode: bool, test_token: str, header: str | None) -> bool:
    """Rate limiting is off in test mode and for a valid test token."""
    return not test_mode and not has_valid_test_token(test_token, header)
