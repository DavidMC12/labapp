"""The field-level error table of SPEC section 7 and the application source."""

from __future__ import annotations

import re
from pathlib import Path

from . import support

_SPEC_PLACEHOLDER = re.compile(r"\{(min|max)\}")
_CODE_PLACEHOLDER = r"\{[^{}\n]+\}"


def test_the_field_error_table_has_unique_codes() -> None:
    rows = support.spec_field_error_rows()
    codes = [row["Code"] for row in rows]

    assert len(codes) == len(set(codes)) == 9


def _message_pattern(message: str) -> re.Pattern[str]:
    """Build a pattern where the SPEC placeholders match any f-string expression."""
    parts: list[str] = []
    position = 0
    for placeholder in _SPEC_PLACEHOLDER.finditer(message):
        parts.append(re.escape(message[position : placeholder.start()]))
        parts.append(_CODE_PLACEHOLDER)
        position = placeholder.end()
    parts.append(re.escape(message[position:]))
    return re.compile("".join(parts))


def _source_texts() -> list[tuple[Path, str]]:
    return [
        (path, path.read_text(encoding="utf-8")) for path in sorted(support.APP_ROOT.rglob("*.py"))
    ]


def test_every_spec_field_message_appears_in_the_application_source() -> None:
    sources = _source_texts()

    missing = [
        (row["Code"], row["Message (es)"])
        for row in support.spec_field_error_rows()
        if not any(_message_pattern(row["Message (es)"]).search(text) for _, text in sources)
    ]

    assert missing == []
