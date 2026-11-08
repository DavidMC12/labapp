"""Tests for the rate limit middleware."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.guards.helpers import FakeMonotonic, make_app, make_settings

PROTECTED = "/api/customers"


def _get(client: TestClient, count: int, headers: object = None) -> list[int]:
    return [client.get(PROTECTED, headers=headers).status_code for _ in range(count)]


def test_the_general_limit_allows_120_and_rejects_the_121st() -> None:
    monotonic = FakeMonotonic()
    client = TestClient(make_app(make_settings(), monotonic))

    assert _get(client, 120) == [401] * 120

    response = client.get(PROTECTED)

    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"
    assert response.headers["x-request-id"]
    body = response.json()
    assert body["code"] == "RATE_LIMITED"
    assert body["retry_after"] == 60
    assert body["detail"] == ("Demasiadas solicitudes. Espera un momento e inténtalo de nuevo.")


def test_the_login_limit_allows_10_and_rejects_the_11th() -> None:
    monotonic = FakeMonotonic()
    client = TestClient(make_app(make_settings(), monotonic))

    for _ in range(10):
        assert client.post("/api/auth/login", json={}).status_code == 422

    response = client.post("/api/auth/login", json={})

    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"


def test_health_is_never_limited() -> None:
    monotonic = FakeMonotonic()
    client = TestClient(make_app(make_settings(), monotonic))

    assert [client.get("/api/health").status_code for _ in range(130)] == [200] * 130
    assert client.get(PROTECTED).status_code == 401


def test_the_window_moves_with_the_monotonic_clock_only() -> None:
    monotonic = FakeMonotonic()
    client = TestClient(make_app(make_settings(), monotonic))
    assert _get(client, 120) == [401] * 120
    assert client.get(PROTECTED).status_code == 429

    monotonic.advance(60)

    assert client.get(PROTECTED).status_code == 401


def test_limits_are_off_in_test_mode() -> None:
    monotonic = FakeMonotonic()
    client = TestClient(make_app(make_settings(test_mode=True), monotonic))

    assert _get(client, 130) == [401] * 130


def test_a_valid_test_token_is_exempt() -> None:
    monotonic = FakeMonotonic()
    client = TestClient(make_app(make_settings(test_token="secret"), monotonic))
    headers = {"X-Test-Token": "secret"}

    assert _get(client, 130, headers) == [401] * 130


def test_a_wrong_test_token_does_not_exempt() -> None:
    monotonic = FakeMonotonic()
    client = TestClient(make_app(make_settings(test_token="secret"), monotonic))
    headers = {"X-Test-Token": "wrong"}

    assert _get(client, 120, headers) == [401] * 120
    assert client.get(PROTECTED, headers=headers).status_code == 429


def test_test_control_paths_count_and_a_valid_token_exempts_them() -> None:
    monotonic = FakeMonotonic()
    client = TestClient(make_app(make_settings(), monotonic))

    assert [client.get("/__test__/x").status_code for _ in range(120)] == [404] * 120
    assert client.get("/__test__/x").status_code == 429


def test_test_control_paths_are_exempt_with_a_valid_token() -> None:
    monotonic = FakeMonotonic()
    client = TestClient(make_app(make_settings(test_token="secret"), monotonic))
    headers = {"X-Test-Token": "secret"}

    assert [client.get("/__test__/x", headers=headers).status_code for _ in range(130)] == [
        404
    ] * 130


def test_separate_buckets_per_client_ip() -> None:
    monotonic = FakeMonotonic()
    client = TestClient(make_app(make_settings(trusted_proxy_count=1), monotonic))
    first = {"X-Forwarded-For": "198.51.100.1, 203.0.113.5"}

    assert _get(client, 120, first) == [401] * 120
    assert client.get(PROTECTED, headers=first).status_code == 429
    assert (
        client.get(
            PROTECTED,
            headers={"X-Forwarded-For": "198.51.100.1, 203.0.113.6"},
        ).status_code
        == 401
    )


def test_a_split_forwarded_for_header_uses_the_last_joined_entry() -> None:
    monotonic = FakeMonotonic()
    client = TestClient(make_app(make_settings(trusted_proxy_count=1), monotonic))
    split = [
        ("X-Forwarded-For", "198.51.100.1"),
        ("X-Forwarded-For", "203.0.113.5"),
    ]

    assert _get(client, 120, split) == [401] * 120
    assert client.get(PROTECTED, headers=split).status_code == 429
    assert client.get(PROTECTED, headers={"X-Forwarded-For": "203.0.113.5"}).status_code == 429
    assert client.get(PROTECTED, headers={"X-Forwarded-For": "198.51.100.1"}).status_code == 401


def test_zero_trusted_proxies_ignores_forwarded_for() -> None:
    monotonic = FakeMonotonic()
    client = TestClient(make_app(make_settings(trusted_proxy_count=0), monotonic))

    for index in range(120):
        assert (
            client.get(
                PROTECTED,
                headers={"X-Forwarded-For": f"198.51.100.{index + 1}"},
            ).status_code
            == 401
        )

    assert client.get(PROTECTED).status_code == 429


def test_one_trusted_proxy_ignores_a_spoofed_leftmost_entry() -> None:
    monotonic = FakeMonotonic()
    client = TestClient(make_app(make_settings(trusted_proxy_count=1), monotonic))

    for index in range(120):
        assert (
            client.get(
                PROTECTED,
                headers={
                    "X-Forwarded-For": f"spoofed-{index}, 203.0.113.5",
                },
            ).status_code
            == 401
        )

    assert (
        client.get(
            PROTECTED,
            headers={"X-Forwarded-For": "203.0.113.5"},
        ).status_code
        == 429
    )


def test_two_trusted_proxies_take_the_second_entry_from_the_right() -> None:
    monotonic = FakeMonotonic()
    client = TestClient(make_app(make_settings(trusted_proxy_count=2), monotonic))
    headers = {"X-Forwarded-For": "198.51.100.1, 203.0.113.5, 10.0.0.1"}

    assert _get(client, 120, headers) == [401] * 120
    assert client.get(PROTECTED, headers=headers).status_code == 429
    assert (
        client.get(
            PROTECTED,
            headers={"X-Forwarded-For": "198.51.100.1, 203.0.113.6, 10.0.0.2"},
        ).status_code
        == 401
    )


def test_reset_limiters_clears_both_limiters() -> None:
    monotonic = FakeMonotonic()
    app = make_app(make_settings(), monotonic)
    client = TestClient(app)
    assert _get(client, 120) == [401] * 120
    assert client.get(PROTECTED).status_code == 429
    app.state.container.reset_limiters()
    assert client.get(PROTECTED).status_code == 401

    for _ in range(10):
        assert client.post("/api/auth/login", json={}).status_code == 422
    assert client.post("/api/auth/login", json={}).status_code == 429
    app.state.container.reset_limiters()
    assert client.post("/api/auth/login", json={}).status_code == 422


def test_the_limited_path_ignores_the_root_path() -> None:
    monotonic = FakeMonotonic()
    client = TestClient(
        make_app(make_settings(), monotonic),
        root_path="/prefix",
    )

    assert [client.get("/prefix/api/customers").status_code for _ in range(120)] == [401] * 120
    assert client.get("/prefix/api/customers").status_code == 429
