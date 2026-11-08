"""Shared paths and document queries for the docs consistency tests."""

from __future__ import annotations

from pathlib import Path

from . import markdown

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_PATH = REPO_ROOT / "docs" / "SPEC.md"
SEED_PATH = REPO_ROOT / "docs" / "SEED.md"
APP_ROOT = REPO_ROOT / "backend" / "app"

SPEC_SECTIONS = (
    "3. Authentication and sessions",
    "4. Customers (flow 1)",
    "5. Orders (flow 2)",
    "6. Invoices and payments (flow 3)",
    "7. Errors and validation order",
)


def spec_text() -> str:
    return SPEC_PATH.read_text(encoding="utf-8")


def seed_text() -> str:
    return SEED_PATH.read_text(encoding="utf-8")


def spec_tables(heading: str) -> list[markdown.Table]:
    return markdown.read_tables(SPEC_PATH, heading)


def seed_tables(heading: str) -> list[markdown.Table]:
    return markdown.read_tables(SEED_PATH, heading)


def table_with(
    tables: list[markdown.Table],
    *headers: str,
) -> markdown.Table:
    """Return the first table whose header row is exactly ``headers``."""
    for table in tables:
        if table and tuple(table[0]) == headers:
            return table
    raise AssertionError(f"no table with headers {headers!r}")


def spec_error_rows() -> list[dict[str, str]]:
    """Return every row of every error table of SPEC sections 3 to 7."""
    rows: list[dict[str, str]] = []
    for heading in SPEC_SECTIONS:
        for table in spec_tables(heading):
            if not table:
                continue
            header = tuple(table[0])
            if "HTTP" in header and "Code" in header and "Message (es)" in header:
                rows.extend(table)
    return rows


def spec_field_error_rows() -> list[dict[str, str]]:
    return table_with(
        spec_tables("7. Errors and validation order"),
        "Code",
        "Message (es)",
    )


def spec_label_rows() -> list[dict[str, str]]:
    return table_with(
        spec_tables("7. Errors and validation order"),
        "Concept",
        "Spanish labels",
    )


def spec_permission_rows() -> list[dict[str, str]]:
    return table_with(
        spec_tables("2. Roles and permissions"),
        "Action",
        "Admin",
        "Sales",
        "Finance",
        "Read-only",
    )


def spec_transition_rows() -> list[dict[str, str]]:
    return table_with(
        spec_tables("5. Orders (flow 2)"),
        "Transition",
        "Allowed from",
        "Who",
        "Effect",
    )


def seed_table(heading: str, *headers: str) -> list[dict[str, str]]:
    return table_with(seed_tables(heading), *headers)
