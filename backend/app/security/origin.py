"""Cross-site request origin checks."""

from __future__ import annotations

from urllib.parse import urlsplit

from app.errors import ApiError

CHECKED_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
ORIGIN_MISMATCH_MESSAGE = "La solicitud no proviene de la aplicación."


def _origin_parts(origin: str) -> tuple[str, str | None, int | None]:
    parts = urlsplit(origin.rstrip("/"))
    return parts.scheme, parts.hostname, parts.port


def check_origin(method: str, origin: str | None, app_origin: str) -> None:
    """Reject state-changing requests whose Origin does not match the app origin."""
    if method.upper() not in CHECKED_METHODS or origin is None:
        return

    try:
        matches = _origin_parts(origin) == _origin_parts(app_origin)
    except ValueError:
        matches = False

    if not matches:
        raise ApiError(403, "CSRF_ORIGIN_MISMATCH", ORIGIN_MISMATCH_MESSAGE)


def cookie_secure(app_origin: str) -> bool:
    """Return whether the session cookie must be marked Secure."""
    return app_origin.startswith("https://")
