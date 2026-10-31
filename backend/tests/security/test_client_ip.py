"""Tests for client IP resolution."""

from __future__ import annotations

import pytest

from app.security.client_ip import client_ip

PEER = "192.0.2.10"
HEADER = "203.0.113.7, 198.51.100.1, 10.0.0.1"


@pytest.mark.parametrize("header", [None, HEADER])
def test_zero_trusted_proxies_uses_the_peer(header: str | None) -> None:
    assert client_ip(PEER, header, 0) == PEER


def test_missing_header_uses_the_peer() -> None:
    assert client_ip(PEER, None, 2) == PEER


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (1, "10.0.0.1"),
        (2, "198.51.100.1"),
        (3, "203.0.113.7"),
    ],
)
def test_entry_counted_from_the_right(count: int, expected: str) -> None:
    assert client_ip(PEER, HEADER, count) == expected


@pytest.mark.parametrize("count", [3, 4, 10])
def test_short_header_uses_the_left_most_entry(count: int) -> None:
    assert client_ip(PEER, "203.0.113.7, 10.0.0.1", count) == "203.0.113.7"


def test_spaces_around_entries_are_stripped() -> None:
    assert client_ip(PEER, "  203.0.113.7 ,  10.0.0.1  ", 1) == "10.0.0.1"


def test_ipv6_entries_are_supported() -> None:
    header = "2001:db8::1, 2001:db8::2"

    assert client_ip(PEER, header, 1) == "2001:db8::2"
    assert client_ip(PEER, header, 2) == "2001:db8::1"


@pytest.mark.parametrize(
    "header",
    [
        "203.0.113.7, not-an-ip",
        "203.0.113.7, 10.0.0.1:8080",
        "203.0.113.7, ",
        "",
    ],
)
def test_invalid_selected_entry_falls_back_to_the_peer(header: str) -> None:
    assert client_ip(PEER, header, 1) == PEER


def test_invalid_unselected_entry_does_not_affect_the_selected_one() -> None:
    assert client_ip(PEER, "not-an-ip, 10.0.0.1", 1) == "10.0.0.1"


@pytest.mark.parametrize("count", [-1, -10])
def test_negative_proxy_count_raises(count: int) -> None:
    with pytest.raises(ValueError):
        client_ip(PEER, HEADER, count)
