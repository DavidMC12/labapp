"""Tests for the allowed origins computed from the settings."""

from __future__ import annotations

import pytest

from app.config import Settings


def test_only_the_app_origin() -> None:
    settings = Settings(app_origin="http://localhost:3000")

    assert settings.allowed_origins == ("http://localhost:3000",)


def test_the_platform_hosts_become_https_origins() -> None:
    settings = Settings(
        app_origin="http://localhost:3000",
        vercel_url="preview.vercel.app",
        vercel_branch_url="branch.vercel.app",
        vercel_project_production_url="production.vercel.app",
    )

    assert settings.allowed_origins == (
        "http://localhost:3000",
        "https://preview.vercel.app",
        "https://branch.vercel.app",
        "https://production.vercel.app",
    )


def test_blank_platform_variables_are_none_and_ignored() -> None:
    settings = Settings(
        app_origin="http://localhost:3000",
        vercel_url="   ",
        vercel_branch_url="",
        vercel_project_production_url="\t",
    )

    assert settings.vercel_url is None
    assert settings.vercel_branch_url is None
    assert settings.vercel_project_production_url is None
    assert settings.allowed_origins == ("http://localhost:3000",)


@pytest.mark.parametrize(
    "app_origin",
    [
        "not-a-url",
        "http://localhost:3000/",
        "http://localhost:3000/path",
        "http://localhost:3000?query=1",
        "http://localhost:3000#fragment",
        "ftp://localhost:3000",
        "http://user:password@localhost:3000",
        "http://localhost:not-a-port",
    ],
)
def test_a_malformed_app_origin_is_ignored(app_origin: str) -> None:
    settings = Settings(app_origin=app_origin)

    assert settings.allowed_origins == ()


@pytest.mark.parametrize(
    "host",
    [
        "preview.vercel.app/path",
        "preview.vercel.app?query=1",
        "bad host",
        "host:not-a-port",
        "https://preview.vercel.app",
    ],
)
def test_a_malformed_platform_host_is_ignored(host: str) -> None:
    settings = Settings(
        app_origin="http://localhost:3000",
        vercel_url=host,
    )

    assert settings.allowed_origins == ("http://localhost:3000",)


def test_duplicates_are_removed() -> None:
    settings = Settings(
        app_origin="https://same.test",
        vercel_url="same.test",
        vercel_branch_url="same.test",
        vercel_project_production_url="same.test",
    )

    assert settings.allowed_origins == ("https://same.test",)


def test_the_platform_variables_are_read_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VERCEL_URL", "preview.vercel.app")

    settings = Settings()

    assert settings.vercel_url == "preview.vercel.app"
    assert "https://preview.vercel.app" in settings.allowed_origins


def test_the_platform_variables_are_not_hidden() -> None:
    settings = Settings(vercel_url="preview.vercel.app")

    assert "vercel_url" in repr(settings)
