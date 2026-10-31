from __future__ import annotations

import pytest

from app.config import Settings
from app.main import create_app


@pytest.mark.parametrize("secret", ["", "   ", "change-me"])
def test_refuses_to_start_without_a_real_session_secret(secret: str) -> None:
    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        create_app(Settings(session_secret=secret, test_mode=False))


@pytest.mark.parametrize("secret", ["", "change-me"])
def test_test_mode_allows_a_placeholder_session_secret(secret: str) -> None:
    app = create_app(Settings(session_secret=secret, test_mode=True))

    assert app.title == "LabApp API"


def test_accepts_a_strong_session_secret() -> None:
    app = create_app(Settings(session_secret="a-long-random-value", test_mode=False))

    assert app.title == "LabApp API"
