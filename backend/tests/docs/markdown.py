"""A small reader for the pipe tables of the project documents.

The documents are Markdown files under ``docs/``. These tests only need their
pipe tables, so this module finds a heading, takes the lines until the next
heading of the same or a higher level, and turns every table in that range into
a list of dictionaries keyed by the header cells. Backticks are removed from
every cell, so ``| `alpha` |`` becomes ``{"Name": "alpha"}`` with the name of
the column from the header row.
"""

from __future__ import annotations

import re
from pathlib import Path

Table = list[dict[str, str]]

_HEADING = re.compile(r"^(?P<level>#{1,6})\s+(?P<text>.*?)\s*#*\s*$")
_SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")
_FENCE = re.compile(r"^\s*(?:```|~~~)")


def _normalize_heading(text: str) -> str:
    return text.strip().lstrip("#").strip()


def _heading(line: str) -> tuple[int, str] | None:
    match = _HEADING.match(line)
    if match is None:
        return None
    return len(match.group("level")), _normalize_heading(match.group("text"))


def _is_row(line: str) -> bool:
    return line.strip().startswith("|")


def _cells(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip().replace("`", "") for cell in stripped.split("|")]


def _is_separator(line: str) -> bool:
    if not _is_row(line):
        return False
    cells = _cells(line)
    return bool(cells) and all(_SEPARATOR_CELL.match(cell) for cell in cells)


def parse_tables(text: str) -> list[Table]:
    """Return every pipe table in the text, in the order they appear."""
    lines = text.splitlines()
    tables: list[Table] = []
    index = 0
    in_fence = False
    while index < len(lines):
        line = lines[index]
        if _FENCE.match(line):
            in_fence = not in_fence
            index += 1
            continue
        if in_fence:
            index += 1
            continue
        if _is_row(line) and index + 1 < len(lines) and _is_separator(lines[index + 1]):
            header = _cells(line)
            index += 2
            rows: Table = []
            while index < len(lines) and _is_row(lines[index]) and not _is_separator(lines[index]):
                cells = _cells(lines[index])
                cells = (cells + [""] * len(header))[: len(header)]
                rows.append(dict(zip(header, cells, strict=True)))
                index += 1
            tables.append(rows)
            continue
        index += 1
    return tables


def tables_under(text: str, heading: str) -> list[Table]:
    """Return the tables under a heading, including its subsections."""
    lines = text.splitlines()
    target = _normalize_heading(heading)
    start: int | None = None
    level = 0
    in_fence = False
    for index, line in enumerate(lines):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        parsed = _heading(line)
        if parsed is None:
            continue
        current_level, current_text = parsed
        if start is None:
            if current_text == target:
                start = index + 1
                level = current_level
        elif current_level <= level:
            return parse_tables("\n".join(lines[start:index]))

    if start is None:
        raise ValueError(f"heading not found: {heading!r}")
    return parse_tables("\n".join(lines[start:]))


def read_tables(path: str | Path, heading: str) -> list[Table]:
    """Read a Markdown file and return the tables under a heading."""
    return tables_under(Path(path).read_text(encoding="utf-8"), heading)
