"""Tests for the committed OpenAPI contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.cli import openapi_document, render_openapi

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPOSITORY_ROOT / "docs" / "openapi.json"
REGENERATE_COMMAND = "cd backend && uv run python -m app.cli openapi --output ../docs/openapi.json"

MONEY_FIELDS = {
    "Order": ("subtotal", "tax_rate", "tax", "total"),
    "OrderLine": ("unit_price", "line_total"),
    "OrderSummary": ("total",),
    "Product": ("price",),
    "Invoice": ("subtotal", "tax_rate", "tax", "total"),
    "InvoiceLine": ("unit_price", "line_total"),
    "InvoiceSummary": ("total",),
    "Payment": ("amount",),
}

MONEY_CASES = [
    (schema_name, field_name)
    for schema_name, field_names in MONEY_FIELDS.items()
    for field_name in field_names
]


def _committed_contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_the_committed_contract_matches_the_application() -> None:
    expected = render_openapi(openapi_document())
    committed = CONTRACT_PATH.read_text(encoding="utf-8")

    assert committed == expected, (
        f"docs/openapi.json is out of date with the application: {REGENERATE_COMMAND}"
    )


def test_every_api_path_is_in_the_contract_with_a_response() -> None:
    contract = _committed_contract()

    for path in openapi_document()["paths"]:
        if not path.startswith("/api"):
            continue
        assert path in contract["paths"], f"{path} is missing: {REGENERATE_COMMAND}"
        for method, operation in contract["paths"][path].items():
            assert operation["responses"], f"{method.upper()} {path} documents no response"


def test_no_operation_is_missing_an_operation_id() -> None:
    contract = _committed_contract()

    for path, operations in contract["paths"].items():
        for method, operation in operations.items():
            assert operation.get("operationId"), f"{method.upper()} {path} has no operationId"


def test_the_contract_hides_the_test_controls() -> None:
    paths = _committed_contract()["paths"]

    assert not [path for path in paths if path.startswith("/__test__")]


@pytest.mark.parametrize(("schema_name", "field_name"), MONEY_CASES)
def test_money_fields_are_strings(schema_name: str, field_name: str) -> None:
    schemas = _committed_contract()["components"]["schemas"]

    assert schemas[schema_name]["properties"][field_name]["type"] == "string", (
        f"{schema_name}.{field_name} must be a string"
    )
