"""Tests that keep docs/PRACTICE.md true to the specification and the code.

The catalog quotes status codes, error codes, Spanish messages and endpoints in
about 120 scenario rows. These tests read those cells and compare them with the
same sources of truth as the other document tests: the error tables of
docs/SPEC.md, backend/app/errors.py, the application source and the OpenAPI
document.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

from app import errors

from . import support

CODE_PATTERN = re.compile(r"[A-Z][A-Z0-9_]{2,}")
CODE_IN_BACKTICKS = re.compile(r"`([^`]+)`")
QUOTED = re.compile(r'"([^"]*)"')
AFTER_MESSAGE_LABEL = re.compile(r'\b(?:message|detail)\b(?:\s*["\']?\s*:)?\s*"([^"]*)"')

# Code-shaped tokens in backticks that are not error codes. Keep this list
# short and explained: every other token must be a code of the SPEC or of the
# application.
NON_CODE_TOKENS: frozenset[str] = frozenset(
    {
        "ACME",  # a search term in A-18, not a code.
        "CARD_DECLINED",  # the gateway's reason value, not an error code.
        "GATEWAY_UNAVAILABLE",  # the gateway's reason value, not an error code.
        "DELETE",  # HTTP methods, quoted as verbs in a few rows.
        "GET",
        "PATCH",
        "POST",
        "PUT",
    }
)


@dataclass(frozen=True)
class Violation:
    """One false row of the catalog, always prefixed with its id."""

    row: str
    message: str

    def __str__(self) -> str:
        return f"PRACTICE {self.row}: {self.message}"


def _report(violations: list[Violation]) -> str:
    return "\n".join(str(violation) for violation in violations)


def _row_codes(row: support.PracticeRow) -> set[str]:
    tokens = CODE_IN_BACKTICKS.findall(" ".join(row.cells))
    return {token for token in tokens if CODE_PATTERN.fullmatch(token)}


def _spec_section_7_codes() -> set[str]:
    text = support.spec_text()
    start = text.index("## 7. Errors and validation order")
    end = text.index("\n## 8.", start)
    tokens = CODE_IN_BACKTICKS.findall(text[start:end])
    return {token for token in tokens if CODE_PATTERN.fullmatch(token)}


def _application_codes() -> set[str]:
    codes = set(errors.ERROR_MESSAGES) | set(errors.FIELD_MESSAGES)
    for name in dir(errors):
        value = getattr(errors, name)
        if isinstance(value, str) and CODE_PATTERN.fullmatch(value):
            codes.add(value)
    return codes


def known_codes() -> set[str]:
    """Every stable code of the SPEC and every code the application defines."""
    return (
        {row["Code"] for row in support.spec_error_rows()}
        | {row["Code"] for row in support.spec_field_error_rows()}
        | _spec_section_7_codes()
        | _application_codes()
    )


def check_codes(rows: list[support.PracticeRow]) -> list[Violation]:
    known = known_codes()
    return [
        Violation(row.id, f"the code '{code}' is not defined")
        for row in rows
        for code in sorted(_row_codes(row) - known - NON_CODE_TOKENS)
    ]


def _template_pattern(template: str) -> re.Pattern[str]:
    """Turn a message with ``{placeholders}`` into a full-match pattern."""
    parts: list[str] = []
    position = 0
    for placeholder in re.finditer(r"\{[^{}\n]+\}", template):
        parts.append(re.escape(template[position : placeholder.start()]))
        parts.append(r".+?")
        position = placeholder.end()
    parts.append(re.escape(template[position:]))
    return re.compile("".join(parts))


def _application_message_patterns() -> list[re.Pattern[str]]:
    """Patterns for every string constant and f-string of backend/app."""
    patterns: list[re.Pattern[str]] = []
    for path in sorted(support.APP_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                patterns.append(re.compile(re.escape(node.value)))
            elif isinstance(node, ast.JoinedStr):
                parts: list[str] = []
                has_text = False
                for value in node.values:
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        parts.append(re.escape(value.value))
                        has_text = has_text or any(char.isalpha() for char in value.value)
                    else:
                        parts.append(r".+?")
                if has_text:
                    patterns.append(re.compile("".join(parts)))
    return patterns


def _frontend_texts() -> list[str]:
    return [
        path.read_text(encoding="utf-8")
        for path in sorted(support.FRONTEND_ROOT.rglob("*"))
        if path.is_file() and path.suffix in {".ts", ".tsx"}
    ]


def _quoted_messages(row: support.PracticeRow) -> set[str]:
    """Messages quoted in the Expected cell.

    The convention found in the rows: a double-quoted text with a space that
    ends with a period and starts with an upper-case letter. The last two
    conditions skip sentence fragments such as "de confirmado a enviado."
    (B-16) and labels such as "Recargar datos". The text after the word
    ``message`` or ``detail`` is also a message even if it breaks that shape.
    """
    quoted = {
        text
        for text in QUOTED.findall(row.expected)
        if " " in text and text.endswith(".") and text[:1].isupper()
    }
    quoted.update(AFTER_MESSAGE_LABEL.findall(row.expected))
    return quoted


def check_messages(rows: list[support.PracticeRow]) -> list[Violation]:
    patterns = _application_message_patterns()
    spec_messages = [
        _template_pattern(row["Message (es)"])
        for row in (*support.spec_error_rows(), *support.spec_field_error_rows())
    ]
    frontend = _frontend_texts()

    def known(message: str) -> bool:
        return any(pattern.fullmatch(message) for pattern in (*patterns, *spec_messages)) or any(
            message in text for text in frontend
        )

    return [
        Violation(row.id, f"the message {message!r} is not defined")
        for row in rows
        for message in sorted(_quoted_messages(row))
        if not known(message)
    ]


def test_the_catalog_has_at_least_a_hundred_scenario_rows() -> None:
    assert len(support.practice_rows()) >= 100


def test_every_row_has_the_seven_cells() -> None:
    wrong = [row.id for row in support.practice_rows() if row.cell_count != 7]
    assert wrong == []


def test_every_id_is_unique_and_has_the_area_form() -> None:
    rows = support.practice_rows()
    ids = [row.id for row in rows]
    malformed = [row.id for row in rows if re.fullmatch(r"[A-H]-\d+", row.id) is None]
    repeated = sorted({identifier for identifier in ids if ids.count(identifier) > 1})
    assert malformed == []
    assert repeated == []


def test_the_numbers_of_each_area_are_consecutive_from_one() -> None:
    numbers: dict[str, list[int]] = {}
    for row in support.practice_rows():
        area, number = row.id.split("-", 1)
        numbers.setdefault(area, []).append(int(number))
    wrong = {
        area: values
        for area, values in numbers.items()
        if sorted(values) != list(range(1, len(values) + 1))
    }
    assert wrong == {}


def test_every_quoted_code_exists() -> None:
    violations = check_codes(support.practice_rows())
    assert violations == [], _report(violations)


def test_every_quoted_spanish_message_exists() -> None:
    violations = check_messages(support.practice_rows())
    assert violations == [], _report(violations)
