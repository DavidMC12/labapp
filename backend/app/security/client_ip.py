"""Client IP resolution behind trusted proxies."""

from __future__ import annotations

from ipaddress import ip_address


def client_ip(peer: str, forwarded_for: str | None, trusted_proxy_count: int) -> str:
    """Return the client IP from X-Forwarded-For or the socket peer."""
    if trusted_proxy_count < 0:
        raise ValueError("trusted_proxy_count must not be negative")

    if trusted_proxy_count == 0 or forwarded_for is None:
        return peer

    entries = [entry.strip() for entry in forwarded_for.split(",")]
    index = len(entries) - trusted_proxy_count
    selected = entries[index] if index >= 0 else entries[0]

    try:
        ip_address(selected)
    except ValueError:
        return peer
    return selected
