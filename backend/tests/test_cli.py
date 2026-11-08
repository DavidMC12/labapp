"""Tests for the database command line."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

import app.cli as cli_module
from app.cli import build_parser, main, reset_refusal, skip_reason


def test_deploy_accepts_the_production_only_flag() -> None:
    arguments = build_parser().parse_args(["deploy", "--production-only"])
    assert arguments.command == "deploy"
    assert arguments.production_only is True
    assert build_parser().parse_args(["deploy"]).production_only is False


def test_unknown_commands_are_rejected() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["drop"])


def test_production_only_runs_in_production_and_outside_the_platform() -> None:
    assert skip_reason(True, {"VERCEL_ENV": "production"}) is None
    assert skip_reason(True, {}) is None
    assert skip_reason(True, {"VERCEL_ENV": ""}) is None


def test_production_only_skips_previews_and_development_deployments() -> None:
    assert "preview" in (skip_reason(True, {"VERCEL_ENV": "preview"}) or "")
    assert skip_reason(True, {"VERCEL_ENV": "development"}) is not None


def test_without_the_flag_nothing_is_skipped() -> None:
    assert skip_reason(False, {"VERCEL_ENV": "preview"}) is None


def test_the_preview_opt_in_is_honored_only_when_exactly_one() -> None:
    assert skip_reason(True, {"VERCEL_ENV": "preview", "RUN_MIGRATIONS_ON_PREVIEW": "1"}) is None
    assert (
        skip_reason(True, {"VERCEL_ENV": "preview", "RUN_MIGRATIONS_ON_PREVIEW": "true"})
        is not None
    )


def test_reset_accepts_its_flags() -> None:
    arguments = build_parser().parse_args(["reset", "--yes", "--allow-public", "--allow-remote"])
    assert arguments.command == "reset"
    assert arguments.yes is True
    assert arguments.allow_public is True
    assert arguments.allow_remote is True

    defaults = build_parser().parse_args(["reset"])
    assert defaults.yes is False
    assert defaults.allow_public is False
    assert defaults.allow_remote is False


def test_the_reset_flags_do_not_abbreviate() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["reset", "--ye"])


@pytest.mark.parametrize(
    ("test_mode", "schema", "yes", "allow_public", "refused"),
    [
        (False, "labapp", True, False, True),
        (True, "labapp", False, False, True),
        (True, "labapp", True, False, False),
        (True, None, True, False, True),
        (True, None, True, True, False),
        (False, None, False, True, True),
    ],
)
def test_reset_refusals(
    test_mode: bool,
    schema: str | None,
    yes: bool,
    allow_public: bool,
    refused: bool,
) -> None:
    reason = reset_refusal(
        test_mode=test_mode,
        schema=schema,
        yes=yes,
        allow_public=allow_public,
    )

    assert (reason is not None) is refused


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "::1", None])
def test_a_local_host_is_allowed(host: str | None) -> None:
    reason = reset_refusal(
        test_mode=True,
        schema="labapp",
        yes=True,
        allow_public=False,
        host=host,
    )

    assert reason is None


@pytest.mark.parametrize("host", ["db.example.com", "10.0.0.5", "::2"])
def test_a_remote_host_needs_the_flag(host: str) -> None:
    refused = reset_refusal(
        test_mode=True,
        schema="labapp",
        yes=True,
        allow_public=False,
        host=host,
    )
    allowed = reset_refusal(
        test_mode=True,
        schema="labapp",
        yes=True,
        allow_public=False,
        host=host,
        allow_remote=True,
    )

    assert refused is not None
    assert host in refused
    assert allowed is None


def test_reset_prints_the_host_and_the_database(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("TEST_MODE", "1")
    monkeypatch.setenv("DATABASE_SCHEMA", "labapp")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://someone:topsecret@localhost:5432/labapp_test",
    )
    calls: list[object] = []
    monkeypatch.setattr(cli_module, "reset_database", calls.append)

    assert main(["reset", "--yes"]) == 0

    printed = capsys.readouterr().out
    assert "localhost" in printed
    assert "labapp_test" in printed
    assert "labapp" in printed
    assert "someone" not in printed
    assert "topsecret" not in printed
    assert len(calls) == 1


def test_reset_refuses_a_remote_host(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("TEST_MODE", "1")
    monkeypatch.setenv("DATABASE_SCHEMA", "labapp")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://someone:topsecret@db.example.com:5432/labapp_test",
    )
    calls: list[object] = []
    monkeypatch.setattr(cli_module, "reset_database", calls.append)

    assert main(["reset", "--yes"]) == 2
    printed = capsys.readouterr().out
    assert "db.example.com" in printed
    assert "topsecret" not in printed
    assert calls == []

    assert main(["reset", "--yes", "--allow-remote"]) == 0
    assert len(calls) == 1


def test_reset_without_test_mode_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_MODE", raising=False)

    assert main(["reset", "--yes"]) == 2


def test_reset_without_a_schema_needs_allow_public(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_MODE", "1")
    monkeypatch.delenv("DATABASE_SCHEMA", raising=False)

    assert main(["reset", "--yes"]) == 2


def test_openapi_prints_the_document(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["openapi"]) == 0

    printed = capsys.readouterr().out
    assert printed.endswith("\n")
    document = json.loads(printed)
    assert document["info"]["title"] == "LabApp API"
    assert "/api/customers" in document["paths"]


def test_openapi_writes_the_document_to_a_file(tmp_path: Path) -> None:
    target = tmp_path / "openapi.json"

    assert main(["openapi", "--output", str(target)]) == 0

    written = target.read_text(encoding="utf-8")
    assert written.endswith("\n")
    assert "/api/invoices/{id}/payments" in json.loads(written)["paths"]


def test_migrate_upgrades_the_database(monkeypatch: pytest.MonkeyPatch) -> None:
    upgrades: list[str] = []
    monkeypatch.setattr(
        cli_module.command, "upgrade", lambda config, revision: upgrades.append(revision)
    )

    assert main(["migrate"]) == 0
    assert upgrades == ["head"]


def test_seed_runs_the_database_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr(cli_module, "seed_database", calls.append)

    assert main(["seed"]) == 0
    assert len(calls) == 1


def test_deploy_migrates_and_seeds(monkeypatch: pytest.MonkeyPatch) -> None:
    steps: list[str] = []
    monkeypatch.delenv("VERCEL_ENV", raising=False)
    monkeypatch.setattr(
        cli_module.command, "upgrade", lambda config, revision: steps.append("upgrade")
    )
    monkeypatch.setattr(cli_module, "seed_database", lambda settings: steps.append("seed"))

    assert main(["deploy"]) == 0
    assert steps == ["upgrade", "seed"]


def test_deploy_skips_a_preview_without_touching_the_database(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    steps: list[str] = []
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setattr(
        cli_module.command, "upgrade", lambda config, revision: steps.append("upgrade")
    )
    monkeypatch.setattr(cli_module, "seed_database", lambda settings: steps.append("seed"))

    assert main(["deploy", "--production-only"]) == 0
    assert steps == []
    assert "preview" in capsys.readouterr().out


def test_reset_without_a_database_url_is_refused(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("TEST_MODE", "1")
    monkeypatch.setenv("DATABASE_SCHEMA", "labapp")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert main(["reset", "--yes"]) == 2
    assert "DATABASE_URL is not set" in capsys.readouterr().out


def test_openapi_restores_a_previous_session_secret(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("SESSION_SECRET", "previous-secret")

    assert main(["openapi"]) == 0
    capsys.readouterr()

    assert os.environ["SESSION_SECRET"] == "previous-secret"


def test_openapi_removes_the_playground_secret_when_there_was_none(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("SESSION_SECRET", raising=False)

    assert main(["openapi"]) == 0
    capsys.readouterr()

    assert "SESSION_SECRET" not in os.environ


class FakeResult:
    def __init__(self, value: int) -> None:
        self.value = value

    def scalar_one(self) -> int:
        return self.value


class FakeConnection:
    def __init__(self, value: int) -> None:
        self.value = value
        self.statements = 0

    def execute(self, statement: object) -> FakeResult:
        self.statements += 1
        return FakeResult(self.value)


class FakeEngine:
    def __init__(self, value: int = 0) -> None:
        self.connection = FakeConnection(value)
        self.disposed = False

    @contextmanager
    def begin(self) -> Iterator[FakeConnection]:
        yield self.connection

    def dispose(self) -> None:
        self.disposed = True


class FakeRepository:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.calls: list[tuple[object, ...]] = []

    def replace_all(self, *args: object, **kwargs: object) -> None:
        self.calls.append(args)


def test_reset_database_builds_the_resetter_and_disposes_the_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = FakeEngine()
    resetters: list[object] = []
    monkeypatch.setattr(cli_module, "create_db_engine", lambda settings: engine)
    monkeypatch.setattr(cli_module, "PostgresCustomerRepository", lambda engine: object())
    monkeypatch.setattr(cli_module, "PostgresOrderStore", lambda engine: object())
    monkeypatch.setattr(cli_module, "PostgresInvoiceStore", lambda engine, gateway: object())

    class RecordingResetter:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.reset_calls = 0
            resetters.append(self)

        def reset(self) -> None:
            self.reset_calls += 1

    monkeypatch.setattr(cli_module, "PostgresResetter", RecordingResetter)

    cli_module.reset_database(cli_module.Settings(session_secret="x"))

    assert len(resetters) == 1
    assert resetters[0].reset_calls == 1  # type: ignore[attr-defined]
    assert engine.disposed is True


def test_seed_database_fills_empty_tables_and_disposes_the_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = FakeEngine(0)
    repositories: list[FakeRepository] = []

    def factory(*args: object, **kwargs: object) -> FakeRepository:
        repository = FakeRepository(*args, **kwargs)
        repositories.append(repository)
        return repository

    monkeypatch.setattr(cli_module, "create_db_engine", lambda settings: engine)
    monkeypatch.setattr(cli_module, "PostgresUserRepository", factory)
    monkeypatch.setattr(cli_module, "PostgresCustomerRepository", factory)
    monkeypatch.setattr(cli_module, "PostgresOrderStore", factory)
    monkeypatch.setattr(cli_module, "PostgresInvoiceStore", factory)

    cli_module.seed_database(cli_module.Settings(session_secret="x"))

    assert engine.connection.statements == 5
    assert [len(repository.calls) for repository in repositories] == [1, 1, 1, 1]
    assert engine.disposed is True


def test_seed_database_leaves_existing_tables_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = FakeEngine(1)
    repositories: list[FakeRepository] = []

    def factory(*args: object, **kwargs: object) -> FakeRepository:
        repository = FakeRepository(*args, **kwargs)
        repositories.append(repository)
        return repository

    monkeypatch.setattr(cli_module, "create_db_engine", lambda settings: engine)
    monkeypatch.setattr(cli_module, "PostgresUserRepository", factory)
    monkeypatch.setattr(cli_module, "PostgresCustomerRepository", factory)
    monkeypatch.setattr(cli_module, "PostgresOrderStore", factory)
    monkeypatch.setattr(cli_module, "PostgresInvoiceStore", factory)

    cli_module.seed_database(cli_module.Settings(session_secret="x"))

    assert repositories == []
    assert engine.disposed is True
