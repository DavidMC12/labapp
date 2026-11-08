"""CSV rendering for the list exports (SPEC section 8, "CSV export").

The writer is pure: it takes the header and the rows and returns the text. It
implements RFC 4180 quoting and the spreadsheet-formula guard of the SPEC without
relying on ``csv.writer``.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

type CsvValue = str | int | Decimal | datetime | None

FORMULA_STARTERS = ("=", "+", "-", "@", "\t", "\r")
CSV_MEDIA_TYPE = "text/csv"
CSV_CONTENT_TYPE = "text/csv; charset=utf-8"
EXPORT_PAGE_SIZE = 500


@dataclass(frozen=True)
class CsvExport:
    """A rendered export: the file name and the UTF-8 text of the file."""

    filename: str
    text: str


def _quote(text: str) -> str:
    if any(character in text for character in (",", '"', "\r", "\n")):
        return '"' + text.replace('"', '""') + '"'
    return text


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _cell(value: CsvValue) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
        if text.startswith(FORMULA_STARTERS):
            text = "'" + text
        return _quote(text)
    if isinstance(value, datetime):
        return _timestamp(value)
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    return str(value)


def write_csv(header: Sequence[str], rows: Iterable[Sequence[CsvValue]]) -> str:
    """Render a header and rows as CSV text.

    Lines end with CRLF, the last one included. A text value that starts with a
    formula starter is prefixed with a single quote before the quoting rules are
    applied, so a spreadsheet never evaluates it. ``None`` is an empty field,
    money (``Decimal``) has two decimals, timestamps are UTC with a trailing
    ``Z`` and no fraction, and integers are plain.
    """
    lines = [",".join(_cell(value) for value in header)]
    lines.extend(",".join(_cell(value) for value in row) for row in rows)
    return "".join(line + "\r\n" for line in lines)


def csv_export_filename(resource: str, now: datetime) -> str:
    """Return ``<resource>-<YYYYMMDD>.csv`` using the UTC date of ``now``."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return f"{resource}-{now.astimezone(UTC):%Y%m%d}.csv"


def csv_response(description: str) -> dict[str, Any]:
    """Document a 200 answer that carries a CSV file of this module."""
    return {
        "description": description,
        "content": {CSV_MEDIA_TYPE: {"schema": {"type": "string"}}},
        "headers": {
            "Content-Disposition": {
                "description": "The attachment file name, with the UTC date of the clock.",
                "schema": {"type": "string"},
            },
            "Cache-Control": {
                "description": "Always `no-store`.",
                "schema": {"type": "string"},
            },
        },
    }
