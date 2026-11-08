"""The configuration refuses an online test mode."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


@pytest.mark.parametrize("deployment", ["production", "preview"])
def test_test_mode_is_refused_on_vercel(
    monkeypatch: pytest.MonkeyPatch,
    deployment: str,
) -> None:
    monkeypatch.setenv("VERCEL_ENV", deployment)

    with pytest.raises(ValidationError, match="TEST_MODE must be off"):
        Settings(session_secret="test-secret", test_mode=True)


@pytest.mark.parametrize("deployment", ["production", "preview"])
def test_a_vercel_deployment_without_test_mode_starts(
    monkeypatch: pytest.MonkeyPatch,
    deployment: str,
) -> None:
    monkeypatch.setenv("VERCEL_ENV", deployment)

    settings = Settings(session_secret="a-long-random-value", test_mode=False)

    assert settings.test_mode is False


@pytest.mark.parametrize("deployment", [None, "development"])
def test_test_mode_is_allowed_outside_a_vercel_deployment(
    monkeypatch: pytest.MonkeyPatch,
    deployment: str | None,
) -> None:
    if deployment is None:
        monkeypatch.delenv("VERCEL_ENV", raising=False)
    else:
        monkeypatch.setenv("VERCEL_ENV", deployment)

    assert Settings(session_secret="test-secret", test_mode=True).test_mode is True
