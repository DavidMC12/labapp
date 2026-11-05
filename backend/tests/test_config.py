from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

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

    monkeypatch.setitem(Settings.model_config, "env_file", ("../.env", ".env"))
    monkeypatch.chdir(backend_dir)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TEST_TOKEN", raising=False)
    monkeypatch.setenv("SESSION_SECRET", "from-environment")

    settings = Settings()

    assert settings.database_url == "postgresql://backend"
    assert settings.test_token == "root-token"
    assert settings.session_secret == "from-environment"


def test_default_configuration_has_no_database() -> None:
    settings = Settings()

    assert settings.database_url is None
    assert settings.database_url_unpooled is None
    assert settings.database_schema is None


def test_env_file_is_read_when_reenabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()
    (backend_dir / ".env").write_text(
        "DATABASE_URL=postgresql://user:password@host/db\n",
        encoding="utf-8",
    )

    monkeypatch.setitem(Settings.model_config, "env_file", ("../.env", ".env"))
    monkeypatch.chdir(backend_dir)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert Settings().database_url == "postgresql://user:password@host/db"


def test_blank_database_values_become_none() -> None:
    settings = Settings(database_url="", database_url_unpooled="   ", database_schema="\t")

    assert settings.database_url is None
    assert settings.database_url_unpooled is None
    assert settings.database_schema is None


def test_database_schema_accepts_a_safe_name() -> None:
    settings = Settings(database_schema="t_0123456789abcdef")

    assert settings.database_schema == "t_0123456789abcdef"


@pytest.mark.parametrize(
    "schema",
    [
        "public",
        "information_schema",
        "pg_x",
        "T_uppercase",
        'quoted"schema',
        "semi;colon",
        "a" * 64,
        "1starts_with_a_digit",
        "has-dash",
    ],
)
def test_database_schema_rejects_unsafe_names(schema: str) -> None:
    with pytest.raises(ValidationError, match="Invalid database schema"):
        Settings(database_schema=schema)


def test_hidden_settings_do_not_appear_in_repr_or_str() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://user:password@host/db",
        database_url_unpooled="postgresql+psycopg://user:password@host/unpooled",
        session_secret="top-secret",
        test_token="secret-token",
    )

    for rendered in (repr(settings), str(settings)):
        assert "top-secret" not in rendered
        assert "secret-token" not in rendered
        assert "postgresql+psycopg://user:password@host/db" not in rendered
        assert "postgresql+psycopg://user:password@host/unpooled" not in rendered


def test_validation_errors_do_not_echo_hidden_values() -> None:
    with pytest.raises(ValidationError) as info:
        Settings(
            default_tax_rate="not-a-number",
            database_url="postgresql+psycopg://user:password@host/db",
            database_url_unpooled="postgresql+psycopg://user:password@host/unpooled",
            session_secret="top-secret",
            test_token="secret-token",
        )

    message = str(info.value)
    assert "top-secret" not in message
    assert "secret-token" not in message
    assert "postgresql+psycopg://user:password@host/db" not in message
    assert "postgresql+psycopg://user:password@host/unpooled" not in message
