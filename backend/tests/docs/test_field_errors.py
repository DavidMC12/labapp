"""The field-level error table of SPEC section 7 and app/errors.py."""

from __future__ import annotations

import pytest

from app.errors import FIELD_MESSAGES

from . import support


def test_the_field_error_table_has_unique_codes() -> None:
    rows = support.spec_field_error_rows()
    codes = [row["Code"] for row in rows]

    assert len(codes) == len(set(codes)) == 9


@pytest.mark.xfail(
    strict=True,
    reason=(
        "app.errors.FIELD_MESSAGES only holds REQUIRED and INVALID_FORMAT. The SPEC "
        "section 7 table also defines TOO_SHORT, TOO_LONG, OUT_OF_RANGE, "
        "REFERENCE_NOT_FOUND, CARD_NUMBER_INVALID, CARD_EXPIRED and CARD_CVC_INVALID; "
        "the code builds those messages as f-strings in the validation modules and "
        "app/domain/payments.py instead of exposing them in the table this test reads."
    ),
)
def test_the_field_error_table_equals_the_code_table_in_app_errors() -> None:
    document = {row["Code"]: row["Message (es)"] for row in support.spec_field_error_rows()}

    assert document == FIELD_MESSAGES
