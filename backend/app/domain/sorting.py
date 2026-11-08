"""Sorting shared by the list endpoints."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from typing import Literal

from app.errors import ApiError

type SortDirection = Literal["asc", "desc"]

_INVALID_MESSAGE = "El formato no es válido."
_VALIDATION_DETAIL = "Revisa los datos ingresados."


@dataclass(frozen=True)
class SortSpec:
    """A validated sort field and direction."""

    field: str
    descending: bool


def _invalid(field: str) -> ApiError:
    return ApiError(
        422,
        "VALIDATION_ERROR",
        _VALIDATION_DETAIL,
        errors=[
            {
                "field": field,
                "code": "INVALID_FORMAT",
                "message": _INVALID_MESSAGE,
            }
        ],
    )


def parse_sort(
    sort: str | None,
    direction: str | None,
    *,
    allowed: Collection[str],
    default: str,
) -> SortSpec:
    """Validate ``sort`` and ``direction`` and build the spec they describe.

    ``direction`` defaults to descending for ``created_at`` and to ascending for
    every other field. When ``sort`` is absent the module's ``default`` field is
    used, so a lone ``direction`` applies to it.
    """
    field = default if sort is None else sort
    if field not in allowed:
        raise _invalid("sort")
    if direction is not None and direction not in ("asc", "desc"):
        raise _invalid("direction")

    descending = direction == "desc" if direction is not None else field == "created_at"
    return SortSpec(field=field, descending=descending)
