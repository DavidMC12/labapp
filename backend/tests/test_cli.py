"""Tests for the database command line."""

from __future__ import annotations

import pytest

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
    arguments = build_parser().parse_args(["reset", "--yes", "--allow-public"])
    assert arguments.command == "reset"
    assert arguments.yes is True
    assert arguments.allow_public is True

    defaults = build_parser().parse_args(["reset"])
    assert defaults.yes is False
    assert defaults.allow_public is False


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


def test_reset_without_test_mode_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_MODE", raising=False)

    assert main(["reset", "--yes"]) == 2


def test_reset_without_a_schema_needs_allow_public(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_MODE", "1")
    monkeypatch.delenv("DATABASE_SCHEMA", raising=False)

    assert main(["reset", "--yes"]) == 2
