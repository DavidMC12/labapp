"""Tests that keep docs/PRACTICE.md true to the specification and the code."""

from __future__ import annotations

import re

from . import support


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
