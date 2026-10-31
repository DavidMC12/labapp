from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings


def test_backend_env_file_wins_and_environment_wins_over_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()

    (tmp_path / ".env").write_text(
        "DATABASE_URL=postgresql://root\nTEST_TOKEN=root-token\nSESSION_SECRET=root-secret\n",
        encoding="utf-8",
    )
    (backend_dir / ".env").write_text(
        "DATABASE_URL=postgresql://backend\nSESSION_SECRET=backend-secret\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(backend_dir)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TEST_TOKEN", raising=False)
    monkeypatch.setenv("SESSION_SECRET", "from-environment")

    settings = Settings()

    assert settings.database_url == "postgresql://backend"
    assert settings.test_token == "root-token"
    assert settings.session_secret == "from-environment"
