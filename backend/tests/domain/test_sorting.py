"""Tests for the shared sort parser."""

from __future__ import annotations

import pytest

from app.domain.sorting import SortSpec, parse_sort
from app.errors import ApiError

CUSTOMER_FIELDS = ("created_at", "name", "email")
PRODUCT_FIELDS = ("id", "sku", "name", "price", "stock")


def customer_sort(sort: str | None, direction: str | None) -> SortSpec:
    return parse_sort(sort, direction, allowed=CUSTOMER_FIELDS, default="created_at")


def test_created_at_descends_and_every_other_field_ascends() -> None:
    assert customer_sort(None, None) == SortSpec("created_at", True)
    assert customer_sort("created_at", None) == SortSpec("created_at", True)
    assert customer_sort("name", None) == SortSpec("name", False)
    assert customer_sort("email", None) == SortSpec("email", False)


def test_direction_overrides_the_default() -> None:
    assert customer_sort("created_at", "asc") == SortSpec("created_at", False)
    assert customer_sort("name", "desc") == SortSpec("name", True)


def test_direction_without_sort_applies_to_the_default_field() -> None:
    assert customer_sort(None, "asc") == SortSpec("created_at", False)
    assert customer_sort(None, "desc") == SortSpec("created_at", True)


def test_the_default_field_is_per_list() -> None:
    assert parse_sort(None, None, allowed=PRODUCT_FIELDS, default="id") == SortSpec("id", False)
    assert parse_sort(None, "desc", allowed=PRODUCT_FIELDS, default="id") == SortSpec("id", True)


@pytest.mark.parametrize("sort", ["", "createdAt", "Name", " NAME", "unknown"])
def test_an_invalid_sort_is_a_validation_error(sort: str) -> None:
    with pytest.raises(ApiError) as error:
        customer_sort(sort, None)

    assert error.value.status == 422
    assert error.value.code == "VALIDATION_ERROR"
    assert error.value.detail == "Revisa los datos ingresados."
    assert error.value.errors == [
        {
            "field": "sort",
            "code": "INVALID_FORMAT",
            "message": "El formato no es válido.",
        }
    ]


@pytest.mark.parametrize("direction", ["", "ASC", "Desc", "ascending", "0"])
def test_an_invalid_direction_is_a_validation_error(direction: str) -> None:
    with pytest.raises(ApiError) as error:
        customer_sort("name", direction)

    assert error.value.errors == [
        {
            "field": "direction",
            "code": "INVALID_FORMAT",
            "message": "El formato no es válido.",
        }
    ]
