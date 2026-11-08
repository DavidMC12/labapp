"""Shared paths and document queries for the docs consistency tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import markdown

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_PATH = REPO_ROOT / "docs" / "SPEC.md"
SEED_PATH = REPO_ROOT / "docs" / "SEED.md"
PRACTICE_PATH = REPO_ROOT / "docs" / "PRACTICE.md"
AUTOMATION_GUIDE_PATH = REPO_ROOT / "docs" / "AUTOMATION_GUIDE.md"
OPENAPI_PATH = REPO_ROOT / "docs" / "openapi.json"
APP_ROOT = REPO_ROOT / "backend" / "app"
FRONTEND_ROOT = REPO_ROOT / "frontend" / "src"

PRACTICE_HEADERS = ("ID", "Level", "Scenario", "Steps", "Expected", "Technique", "Diff")

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


@dataclass(frozen=True)
class PracticeRow:
    """One scenario row of ``docs/PRACTICE.md`` with its cells as written."""

    id: str
    level: str
    scenario: str
    steps: str
    expected: str
    technique: str
    difficulty: str
    executed: bool
    cells: tuple[str, ...]

    @property
    def cell_count(self) -> int:
        return len(self.cells)

    @property
    def area(self) -> str:
        return self.id.split("-", 1)[0]


def practice_text(source: str | Path | None = None) -> str:
    """Return the catalog text from the default path, a file or a string."""
    if source is None:
        return PRACTICE_PATH.read_text(encoding="utf-8")
    if isinstance(source, Path):
        return source.read_text(encoding="utf-8")
    return source


def practice_rows(source: str | Path | None = None) -> list[PracticeRow]:
    """Read every scenario row, skipping the legend table of the document."""
    rows: list[PracticeRow] = []
    for table in markdown.raw_tables(practice_text(source)):
        if tuple(table.header) != PRACTICE_HEADERS:
            continue
        for cells in table.rows:
            values = cells + [""] * (len(PRACTICE_HEADERS) - len(cells))
            record = dict(zip(PRACTICE_HEADERS, values, strict=False))
            raw_id = record["ID"]
            rows.append(
                PracticeRow(
                    id=raw_id.replace("✔", "").strip(),
                    level=record["Level"],
                    scenario=record["Scenario"],
                    steps=record["Steps"],
                    expected=record["Expected"],
                    technique=record["Technique"],
                    difficulty=record["Diff"],
                    executed="✔" in raw_id,
                    cells=tuple(cells),
                )
            )
    return rows


def test_control_endpoints() -> set[tuple[str, str]]:
    """The documented ``/__test__`` method and path pairs."""
    pairs: set[tuple[str, str]] = set()
    for table in markdown.tables_under(
        AUTOMATION_GUIDE_PATH.read_text(encoding="utf-8"), "11. The test controls"
    ):
        if not table or tuple(table[0]) != ("Method", "Path", "Body", "Answer"):
            continue
        pairs.update((row["Method"], row["Path"]) for row in table)
    return pairs
