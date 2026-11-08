"""Tests for the small Markdown table reader."""

from __future__ import annotations

from . import markdown

DOCUMENT = """# Title

## Section

| Name | Value | Note |
|:---|---:|:---:|
| `alpha` | 1 | |
| beta | 2 | plain |
| gamma | 3 | with `code` |

## Other

| Name | Value |
|---|---|
| delta | 4 |
"""


def test_tables_under_a_heading_returns_dict_rows() -> None:
    tables = markdown.tables_under(DOCUMENT, "Section")

    assert tables == [
        [
            {"Name": "alpha", "Value": "1", "Note": ""},
            {"Name": "beta", "Value": "2", "Note": "plain"},
            {"Name": "gamma", "Value": "3", "Note": "with code"},
        ]
    ]


def test_tables_under_stops_at_the_next_heading_of_the_same_level() -> None:
    tables = markdown.tables_under(DOCUMENT, "Other")

    assert tables == [[{"Name": "delta", "Value": "4"}]]


def test_tables_under_accepts_a_heading_with_or_without_hashes() -> None:
    assert markdown.tables_under(DOCUMENT, "## Section") == markdown.tables_under(
        DOCUMENT, "Section"
    )


def test_tables_under_ignores_tables_inside_fenced_code() -> None:
    document = """## Section

```text
| Name | Value |
|---|---|
| nope | 0 |
```

| Name | Value |
|---|---|
| yes | 1 |
"""

    assert markdown.tables_under(document, "Section") == [[{"Name": "yes", "Value": "1"}]]


def test_tables_under_raises_for_a_missing_heading() -> None:
    try:
        markdown.tables_under(DOCUMENT, "Missing")
    except ValueError as error:
        assert "Missing" in str(error)
    else:  # pragma: no cover - the assertion above is the point
        raise AssertionError("a missing heading must raise")


def test_read_tables_reads_a_file(tmp_path) -> None:
    path = tmp_path / "document.md"
    path.write_text(DOCUMENT, encoding="utf-8")

    assert markdown.read_tables(path, "Section")[0][0] == {
        "Name": "alpha",
        "Value": "1",
        "Note": "",
    }
