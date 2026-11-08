"""Tests for the committed OpenAPI contract."""

from __future__ import annotations

from pathlib import Path

from app.cli import openapi_document, render_openapi

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPOSITORY_ROOT / "docs" / "openapi.json"
REGENERATE_COMMAND = "cd backend && uv run python -m app.cli openapi --output ../docs/openapi.json"


def test_the_committed_contract_matches_the_application() -> None:
    expected = render_openapi(openapi_document())
    committed = CONTRACT_PATH.read_text(encoding="utf-8")

    assert committed == expected, (
        f"docs/openapi.json is out of date with the application: {REGENERATE_COMMAND}"
    )
