"""Tests for the pure customer CSV parser."""

from __future__ import annotations

import pytest

from app.domain.csv_import import CustomerCsv, parse_customer_csv


def parse(text: str, filename: str = "customers.csv") -> CustomerCsv:
    return parse_customer_csv(text.encode("utf-8"), filename)


def assert_file_error(
    result: CustomerCsv,
    code: str,
    message: str,
) -> None:
    assert result.header == ()
    assert result.rows == ()
    assert result.errors == ({"field": "file", "code": code, "message": message},)


def test_parses_a_clean_file() -> None:
    result = parse(
        "name,email,phone,tax_id,address\n"
        "Acme,acme@example.test,+1 555,ACME-1,Av. Principal 1\n"
        "Beta,beta@example.test,,,\n"
    )

    assert result.errors == ()
    assert result.header == ("name", "email", "phone", "tax_id", "address")
    assert result.rows[0].line == 2
    assert result.rows[0].cells == (
        "Acme",
        "acme@example.test",
        "+1 555",
        "ACME-1",
        "Av. Principal 1",
    )
    assert result.rows[1].line == 3
    assert result.rows[1].cells == ("Beta", "beta@example.test", "", "", "")


def test_ignores_a_leading_byte_order_mark() -> None:
    content = b"\xef\xbb\xbfname,email\nAcme,acme@example.test\n"

    result = parse_customer_csv(content, "customers.csv")

    assert result.errors == ()
    assert result.header == ("name", "email")
    assert result.rows[0].cells == ("Acme", "acme@example.test")


@pytest.mark.parametrize("end", ["\r\n", "\n"])
def test_accepts_crlf_and_lf_endings(end: str) -> None:
    text = end.join(
        [
            "name,email",
            "Acme,acme@example.test",
            "Beta,beta@example.test",
        ]
    )

    result = parse(text + end)

    assert result.errors == ()
    assert [row.line for row in result.rows] == [2, 3]
    assert [row.cells[0] for row in result.rows] == ["Acme", "Beta"]


def test_quoted_fields_hold_commas_quotes_and_line_breaks() -> None:
    text = (
        'name,email,address\n'
        '"Acme, S.A.",acme@example.test,"Calle 1, ""Piso 2"""\n'
        '"Beta\nComercial",beta@example.test,Calle 3\n'
        "Gamma,gamma@example.test,Calle 4\n"
    )

    result = parse(text)

    assert result.errors == ()
    assert result.rows[0].cells == ("Acme, S.A.", "acme@example.test", 'Calle 1, "Piso 2"')
    assert result.rows[1].line == 3
    assert result.rows[1].cells == ("Beta\nComercial", "beta@example.test", "Calle 3")
    assert result.rows[2].line == 5


def test_blank_lines_are_ignored_but_counted_in_the_line_numbers() -> None:
    text = (
        "name,email\n"
        "\n"
        "Acme,acme@example.test\n"
        "   \n"
        "\n"
        "Beta,beta@example.test\n"
    )

    result = parse(text)

    assert result.errors == ()
    assert [row.line for row in result.rows] == [3, 6]
    assert [row.cells[0] for row in result.rows] == ["Acme", "Beta"]


def test_header_cells_are_trimmed() -> None:
    result = parse(" name , email , phone \nAcme,acme@example.test,+1 555\n")

    assert result.errors == ()
    assert result.header == ("name", "email", "phone")


def test_optional_columns_may_be_absent() -> None:
    result = parse("name,email\nAcme,acme@example.test\n")

    assert result.errors == ()
    assert result.header == ("name", "email")
    assert result.rows[0].cells == ("Acme", "acme@example.test")


def test_an_empty_file_is_required() -> None:
    assert_file_error(
        parse_customer_csv(b"", "customers.csv"),
        "REQUIRED",
        "Este campo es obligatorio.",
    )


def test_a_file_with_only_the_header_is_out_of_range() -> None:
    assert_file_error(
        parse("name,email\n"),
        "OUT_OF_RANGE",
        "El valor debe estar entre 1 y 200.",
    )


def test_two_hundred_rows_are_accepted() -> None:
    lines = ["name,email"] + [f"Customer {index},c{index}@example.test" for index in range(200)]

    result = parse("\n".join(lines) + "\n")

    assert result.errors == ()
    assert len(result.rows) == 200


def test_two_hundred_and_one_rows_are_out_of_range() -> None:
    lines = ["name,email"] + [f"Customer {index},c{index}@example.test" for index in range(201)]

    assert_file_error(
        parse("\n".join(lines) + "\n"),
        "OUT_OF_RANGE",
        "El valor debe estar entre 1 y 200.",
    )


def test_a_name_without_the_csv_extension_is_invalid() -> None:
    assert_file_error(
        parse("name,email\nAcme,acme@example.test\n", "customers.txt"),
        "INVALID_FORMAT",
        "El formato no es válido.",
    )


def test_the_extension_is_case_insensitive() -> None:
    result = parse("name,email\nAcme,acme@example.test\n", "CUSTOMERS.CSV")

    assert result.errors == ()
    assert result.rows[0].cells[0] == "Acme"


def test_invalid_utf8_is_invalid() -> None:
    content = b"name,email\nAcme\xff,acme@example.test\n"

    assert_file_error(
        parse_customer_csv(content, "customers.csv"),
        "INVALID_FORMAT",
        "El formato no es válido.",
    )


@pytest.mark.parametrize(
    "header",
    [
        "name,email,status",
        "name,email,name",
        "name,email,email",
        "email,phone",
    ],
    ids=["unknown-column", "duplicated-name", "duplicated-email", "missing-name"],
)
def test_an_invalid_header_is_invalid(header: str) -> None:
    assert_file_error(
        parse(f"{header}\nAcme,acme@example.test\n"),
        "INVALID_FORMAT",
        "El formato no es válido.",
    )


def test_a_missing_email_column_is_invalid() -> None:
    assert_file_error(
        parse("name,phone\nAcme,+1 555\n"),
        "INVALID_FORMAT",
        "El formato no es válido.",
    )


def test_a_blank_only_file_has_no_header() -> None:
    assert_file_error(
        parse("\n\n   \n"),
        "INVALID_FORMAT",
        "El formato no es válido.",
    )


def test_rows_with_missing_or_extra_cells_are_returned_not_rejected_whole() -> None:
    result = parse(
        "name,email,phone\n"
        "Acme,acme@example.test\n"
        "Beta,beta@example.test,+1 555,extra\n"
    )

    assert result.errors == ()
    assert [row.line for row in result.rows] == [2, 3]
    assert [len(row.cells) for row in result.rows] == [2, 4]
