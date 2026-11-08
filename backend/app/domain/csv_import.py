"""Parsing for the customer CSV import (SPEC section 4, "Import").

The parser is pure: it takes the bytes of the uploaded file and its name and
returns the header and the data rows with their physical line numbers, or the
whole-file errors. It never validates the field values of a row; that is the
job of the same validation the creation uses.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

COLUMNS = ("name", "email", "phone", "tax_id", "address")
MIN_ROWS = 1
MAX_ROWS = 200

REQUIRED_MESSAGE = "Este campo es obligatorio."
INVALID_FORMAT_MESSAGE = "El formato no es válido."
OUT_OF_RANGE_MESSAGE = "El valor debe estar entre 1 y 200."

type FieldProblem = dict[str, str]


@dataclass(frozen=True)
class CsvRow:
    """One non-blank data record and the physical line where it starts."""

    line: int
    cells: tuple[str, ...]


@dataclass(frozen=True)
class CustomerCsv:
    """The parsed file, or the whole-file errors that reject it."""

    header: tuple[str, ...] = ()
    rows: tuple[CsvRow, ...] = ()
    errors: tuple[FieldProblem, ...] = ()


def _failed(code: str, message: str) -> CustomerCsv:
    return CustomerCsv(errors=({"field": "file", "code": code, "message": message},))


def _is_blank(cells: tuple[str, ...]) -> bool:
    """A record is blank when it has no cells or one whitespace-only cell."""
    return not cells or (len(cells) == 1 and not cells[0].strip())


def _records(text: str) -> list[tuple[int, tuple[str, ...]]]:
    """Return every record with the physical line where it starts.

    ``csv.reader`` consumes a quoted field with line breaks as one record; its
    ``line_num`` is the line where the record ends, so the start is the previous
    end plus one. Blank records are kept here because they move the line number.
    """
    reader = csv.reader(io.StringIO(text, newline=""))
    records: list[tuple[int, tuple[str, ...]]] = []
    previous_end = 0
    for cells in reader:
        records.append((previous_end + 1, tuple(cells)))
        previous_end = reader.line_num
    return records


def parse_customer_csv(content: bytes, filename: str | None) -> CustomerCsv:
    """Parse an uploaded customer file or return its whole-file errors."""
    if not content:
        return _failed("REQUIRED", REQUIRED_MESSAGE)
    if filename is None or not filename.lower().endswith(".csv"):
        return _failed("INVALID_FORMAT", INVALID_FORMAT_MESSAGE)
    try:
        text = content.decode("utf-8-sig")
        records = _records(text)
    except (UnicodeDecodeError, csv.Error):
        return _failed("INVALID_FORMAT", INVALID_FORMAT_MESSAGE)

    header: tuple[str, ...] | None = None
    rows: list[CsvRow] = []
    for line, cells in records:
        if _is_blank(cells):
            continue
        if header is None:
            header = tuple(cell.strip() for cell in cells)
        else:
            rows.append(CsvRow(line=line, cells=cells))

    if header is None:
        return _failed("INVALID_FORMAT", INVALID_FORMAT_MESSAGE)
    if (
        len(set(header)) != len(header)
        or any(column not in COLUMNS for column in header)
        or "name" not in header
        or "email" not in header
    ):
        return _failed("INVALID_FORMAT", INVALID_FORMAT_MESSAGE)
    if not MIN_ROWS <= len(rows) <= MAX_ROWS:
        return _failed("OUT_OF_RANGE", OUT_OF_RANGE_MESSAGE)

    return CustomerCsv(header=header, rows=tuple(rows))


__all__ = ["COLUMNS", "CustomerCsv", "CsvRow", "MAX_ROWS", "MIN_ROWS", "parse_customer_csv"]
