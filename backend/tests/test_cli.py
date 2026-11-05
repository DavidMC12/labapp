"""Tests for the database command line."""

from __future__ import annotations

import pytest

from app.cli import build_parser, skip_reason


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
