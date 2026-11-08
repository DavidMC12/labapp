"""Tests for the pure CSV writer of the list exports."""

from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from io import StringIO

import pytest

from app.domain.csv_export import csv_export_filename, write_csv


def rows_of(text: str) -> list[list[str]]:
    return list(csv.reader(StringIO(text)))


def test_plain_values_are_written_unchanged() -> None:
    text = write_csv(("id", "name"), [(1, "Acme"), (2, "Beta")])

    assert text == "id,name\r\n1,Acme\r\n2,Beta\r\n"


def test_every_line_ends_with_crlf_including_the_last_one() -> None:
    text = write_csv(("id",), [(1,), (2,)])

    assert text.endswith("\r\n")
    assert text.count("\r\n") == 3


def test_an_empty_table_keeps_the_header_line() -> None:
    assert write_csv(("id", "name"), []) == "id,name\r\n"


def test_a_comma_is_quoted() -> None:
    assert write_csv(("value",), [("a, b",)]) == 'value\r\n"a, b"\r\n'


def test_a_double_quote_is_doubled_and_quoted() -> None:
    assert write_csv(("value",), [('say "hi"',)]) == 'value\r\n"say ""hi"""\r\n'


@pytest.mark.parametrize("value", ["Line 1\r\nLine 2", "Line 1\nLine 2", "Solo\r"])
def test_a_line_break_is_quoted(value: str) -> None:
    text = write_csv(("address",), [(value,)])

    assert text == f'address\r\n"{value.replace(chr(34), chr(34) * 2)}"\r\n'


def test_unicode_is_kept_as_it_is() -> None:
    text = write_csv(("name",), [("Ñandú",), ("日本",)])

    assert rows_of(text) == [["name"], ["Ñandú"], ["日本"]]


def test_none_is_an_empty_field() -> None:
    assert write_csv(("phone",), [(None,)]) == "phone\r\n\r\n"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("=1+1", "'=1+1"),
        ("+1+1", "'+1+1"),
        ("-1+1", "'-1+1"),
        ("@sum", "'@sum"),
        ("\ttext", "'\ttext"),
        ("\rtext", '"\'\rtext"'),
        ("-", "'-"),
    ],
)
def test_a_formula_starter_gets_a_single_quote(value: str, expected: str) -> None:
    assert write_csv(("value",), [(value,)]) == f"value\r\n{expected}\r\n"


def test_the_formula_guard_runs_before_the_quoting_rules() -> None:
    assert write_csv(("value",), [("-5, x",)]) == 'value\r\n"\'-5, x"\r\n'


def test_a_parsed_formula_field_keeps_the_leading_quote() -> None:
    text = write_csv(("name",), [('=HYPERLINK("http://x","y")',)])

    assert rows_of(text)[1] == ['\'=HYPERLINK("http://x","y")']


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("0"), "0.00"),
        (Decimal("1.5"), "1.50"),
        (Decimal("110"), "110.00"),
        (Decimal("110.55"), "110.55"),
    ],
)
def test_money_has_two_decimals_and_no_quotes(value: Decimal, expected: str) -> None:
    assert write_csv(("total",), [(value,)]) == f"total\r\n{expected}\r\n"


def test_integers_are_plain_and_never_quoted() -> None:
    assert write_csv(("id", "line"), [(1, -5)]) == "id,line\r\n1,-5\r\n"


def test_a_negative_integer_is_not_a_formula() -> None:
    assert rows_of(write_csv(("quantity",), [(-5,)])) == [["quantity"], ["-5"]]


@pytest.mark.parametrize(
    "value",
    [
        datetime(2026, 10, 31, 14, 30, tzinfo=UTC),
        datetime(2026, 10, 31, 14, 30, 0, 500000, tzinfo=UTC),
        datetime(2026, 10, 31, 9, 30, tzinfo=timezone(timedelta(hours=-5))),
    ],
)
def test_a_timestamp_is_utc_iso_without_a_fraction(value: datetime) -> None:
    assert rows_of(write_csv(("created_at",), [(value,)]))[1] == ["2026-10-31T14:30:00Z"]


def test_the_filename_uses_the_utc_date_of_the_clock() -> None:
    now = datetime(2026, 11, 5, 23, 30, tzinfo=UTC)

    assert csv_export_filename("customers", now) == "customers-20261105.csv"
    assert csv_export_filename("orders", now + timedelta(hours=1)) == "orders-20261106.csv"
