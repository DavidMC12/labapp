"""Global origin check for state-changing API requests."""

from __future__ import annotations

from fastapi import Request

from app.errors import ApiError
from app.security.origin import CHECKED_METHODS, ORIGIN_MISMATCH_MESSAGE, check_origin


def origin_guard(request: Request) -> None:
    """Reject a state-changing request whose Origin matches no allowed origin."""
    if not request.url.path.startswith("/api/"):
        return

    origin = request.headers.get("origin")
    if request.method.upper() not in CHECKED_METHODS or origin is None:
        return

    for allowed in request.app.state.settings.allowed_origins:
        try:
            check_origin(request.method, origin, allowed)
        except ApiError:
            continue
        return

    raise ApiError(403, "CSRF_ORIGIN_MISMATCH", ORIGIN_MISMATCH_MESSAGE)
