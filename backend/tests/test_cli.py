"""Tests for the database command line."""

from __future__ import annotations

import json
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
