"""Tests for the committed OpenAPI contract."""

from __future__ import annotations

import importlib.metadata
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from app.cli import openapi_document, render_openapi

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPOSITORY_ROOT / "docs" / "openapi.json"
REGENERATE_COMMAND = "cd backend && uv run python -m app.cli openapi --output ../docs/openapi.json"

PROBLEM_MEDIA_TYPE = "application/problem+json"
PROBLEM_REF = "#/components/schemas/Problem"
COOKIE_SCHEME = "cookieAuth"
STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
PUBLIC_OPERATIONS = {
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/logout"),
    ("GET", "/api/health"),
}
LOGIN = ("POST", "/api/auth/login")
MONEY_PATTERN = r"^[0-9]+\.[0-9]{2}$"
TAX_RATE_PATTERN = r"^[0-9]{1,3}(\.[0-9]{1,2})?$"
PAYMENT_AMOUNT_PATTERN = r"^[0-9]{1,10}(\.[0-9]{1,2})?$"
ID_MINIMUM = 1
ID_MAXIMUM = 2147483647

MONEY_FIELDS = {
    "Order": ("subtotal", "tax_rate", "tax", "total"),
    "OrderLine": ("unit_price", "line_total"),
    "OrderSummary": ("total",),
    "Product": ("price",),
    "TaxRateOut": ("tax_rate",),
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

BOUNDED_SCHEMAS = (
    "CustomerOut",
    "Product",
    "OrderLine",
    "OrderCustomer",
    "Order",
    "OrderSummary",
    "InvoiceCustomer",
    "InvoiceLine",
    "Payment",
    "Invoice",
    "InvoiceSummary",
    "Shortage",
)


def _committed_contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _operations(
    contract: dict[str, Any],
) -> Iterator[tuple[str, str, dict[str, Any]]]:
    for path, operations in contract["paths"].items():
        for method, operation in operations.items():
            yield path, method.upper(), operation


def _non_null(schema: dict[str, Any]) -> dict[str, Any]:
    for option in schema.get("anyOf", []):
        if option.get("type") != "null":
            return option
    return schema


def _description(operation: dict[str, Any], status: int) -> str:
    return operation["responses"][str(status)]["description"]


def _references(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        reference = value.get("$ref")
        if isinstance(reference, str):
            yield reference
        for nested in value.values():
            yield from _references(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _references(nested)


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


def test_every_error_answer_uses_the_problem_component() -> None:
    contract = _committed_contract()

    for path, method, operation in _operations(contract):
        for status, response in operation["responses"].items():
            if not status.isdigit() or int(status) < 400:
                continue
            content = response.get("content")
            assert content is not None, f"{method} {path} {status} documents no body"
            assert list(content) == [PROBLEM_MEDIA_TYPE], f"{method} {path} {status}"
            assert content[PROBLEM_MEDIA_TYPE]["schema"] == {"$ref": PROBLEM_REF}, (
                f"{method} {path} {status} does not reference the Problem component"
            )


def test_the_problem_component_describes_the_error_members() -> None:
    schemas = _committed_contract()["components"]["schemas"]
    problem = schemas["Problem"]

    assert problem["type"] == "object"
    assert set(problem["required"]) == {"type", "title", "status", "code", "detail"}
    properties = problem["properties"]
    assert {
        "type",
        "title",
        "status",
        "code",
        "detail",
        "errors",
        "payment_id",
        "reason",
    } <= set(properties)
    assert _non_null(properties["errors"])["type"] == "array"
    assert _non_null(properties["errors"])["items"] == {"$ref": "#/components/schemas/FieldError"}
    assert _non_null(properties["payment_id"])["type"] == "integer"
    assert _non_null(properties["reason"])["type"] == "string"

    field_error = schemas["FieldError"]
    assert set(field_error["required"]) == {"field", "code", "message"}
    for name in ("field", "code", "message"):
        assert field_error["properties"][name]["type"] == "string"


def test_every_operation_documents_the_answers_that_apply_to_it() -> None:
    contract = _committed_contract()

    for path, method, operation in _operations(contract):
        responses = operation["responses"]
        operation_name = f"{method} {path}"
        has_body = "requestBody" in operation
        protected = (method, path) not in PUBLIC_OPERATIONS
        health = (method, path) == ("GET", "/api/health")

        assert ("400" in responses) is has_body, operation_name
        assert ("413" in responses) is has_body, operation_name
        assert ("401" in responses) is (protected or (method, path) == LOGIN), operation_name
        assert ("403" in responses) is (method in STATE_CHANGING_METHODS), operation_name
        assert ("429" in responses) is (not health), operation_name
        assert "500" in responses, operation_name
        assert ("503" in responses) is (not health), operation_name

        if has_body:
            assert "MALFORMED_JSON" in _description(operation, 400), operation_name
            assert "PAYLOAD_TOO_LARGE" in _description(operation, 413), operation_name
        if protected:
            assert "UNAUTHENTICATED" in _description(operation, 401), operation_name
            assert "SESSION_EXPIRED" in _description(operation, 401), operation_name
        if (method, path) == LOGIN:
            assert "INVALID_CREDENTIALS" in _description(operation, 401), operation_name
        if method in STATE_CHANGING_METHODS:
            assert "CSRF_ORIGIN_MISMATCH" in _description(operation, 403), operation_name
        if not health:
            assert "RATE_LIMITED" in _description(operation, 429), operation_name
            assert "LOCK_TIMEOUT" in _description(operation, 503), operation_name
        assert "INTERNAL_ERROR" in _description(operation, 500), operation_name

    login = contract["paths"]["/api/auth/login"]["post"]
    assert "SERVICE_BUSY" in _description(login, 503)
    payment = contract["paths"]["/api/invoices/{id}/payments"]["post"]
    assert "PAYMENT_GATEWAY_UNAVAILABLE" in _description(payment, 503)
    create_customer = contract["paths"]["/api/customers"]["post"]
    assert "FORBIDDEN" in _description(create_customer, 403)
    patch_settings = contract["paths"]["/api/settings"]["patch"]
    assert "FORBIDDEN" in _description(patch_settings, 403)


def test_the_cookie_scheme_marks_the_protected_operations() -> None:
    contract = _committed_contract()
    scheme = contract["components"]["securitySchemes"][COOKIE_SCHEME]

    assert scheme["type"] == "apiKey"
    assert scheme["in"] == "cookie"
    assert scheme["name"] == "labapp_session"
    assert scheme["description"]

    public: set[tuple[str, str]] = set()
    for path, method, operation in _operations(contract):
        security = operation.get("security")
        if security:
            assert security == [{COOKIE_SCHEME: []}], f"{method} {path}"
        else:
            public.add((method, path))

    assert public == PUBLIC_OPERATIONS


def test_the_payment_body_is_a_component() -> None:
    contract = _committed_contract()
    schemas = contract["components"]["schemas"]
    payment = schemas["PaymentCreate"]

    assert set(payment["properties"]) == {"method", "amount", "card", "reference"}
    assert set(payment["required"]) == {"method", "amount"}
    assert payment["properties"]["method"]["enum"] == ["card", "transfer", "cash"]
    assert payment["properties"]["amount"]["pattern"] == PAYMENT_AMOUNT_PATTERN
    assert "example" in payment["properties"]["amount"]
    assert _non_null(payment["properties"]["card"]) == {"$ref": "#/components/schemas/PaymentCard"}
    card = schemas["PaymentCard"]
    assert set(card["properties"]) == {"number", "expiry", "cvc"}
    for name in ("number", "expiry", "cvc"):
        assert card["properties"][name]["type"] == "string"

    operation = contract["paths"]["/api/invoices/{id}/payments"]["post"]
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/PaymentCreate"
    }
    for method in ("card", "transfer", "cash"):
        assert method in payment["description"]


@pytest.mark.parametrize(("schema_name", "field_name"), MONEY_CASES)
def test_money_fields_are_strings(schema_name: str, field_name: str) -> None:
    schemas = _committed_contract()["components"]["schemas"]

    assert schemas[schema_name]["properties"][field_name]["type"] == "string", (
        f"{schema_name}.{field_name} must be a string"
    )


@pytest.mark.parametrize(("schema_name", "field_name"), MONEY_CASES)
def test_money_fields_carry_the_pattern_and_an_example(schema_name: str, field_name: str) -> None:
    schemas = _committed_contract()["components"]["schemas"]
    field = schemas[schema_name]["properties"][field_name]

    assert field["pattern"] == MONEY_PATTERN, f"{schema_name}.{field_name}"
    assert field["example"] == "19.90", f"{schema_name}.{field_name}"


def test_the_tax_rate_input_documents_its_pattern_and_example() -> None:
    schemas = _committed_contract()["components"]["schemas"]
    field = _non_null(schemas["SettingsPatch"]["properties"]["tax_rate"])

    assert field["pattern"] == TAX_RATE_PATTERN
    assert field["example"] == "10.00"


def test_id_and_version_fields_document_their_bounds() -> None:
    schemas = _committed_contract()["components"]["schemas"]

    for schema_name in BOUNDED_SCHEMAS:
        for field_name, field in schemas[schema_name]["properties"].items():
            if field_name != "id" and field_name != "version" and not field_name.endswith("_id"):
                continue
            integer = _non_null(field)
            if integer.get("type") != "integer":
                continue
            assert integer["minimum"] == ID_MINIMUM, f"{schema_name}.{field_name}"
            assert integer["maximum"] == ID_MAXIMUM, f"{schema_name}.{field_name}"


def test_every_reference_resolves() -> None:
    contract = _committed_contract()

    for reference in _references(contract):
        node: Any = contract
        for part in reference.removeprefix("#/").split("/"):
            assert part in node, f"{reference} does not resolve"
            node = node[part]


def test_the_document_has_the_expected_metadata() -> None:
    contract = _committed_contract()
    info = contract["info"]

    assert info["title"] == "LabApp API"
    assert info["version"] == importlib.metadata.version("labapp-backend")
    assert "docs/SPEC.md" in info["description"]
    assert contract["servers"] == [{"url": "/"}]

    tags = contract["tags"]
    assert [tag["name"] for tag in tags] == [
        "auth",
        "customers",
        "orders",
        "invoices",
        "health",
    ]
    assert all(tag.get("description") for tag in tags)
    known = {tag["name"] for tag in tags}
    for path, method, operation in _operations(contract):
        assert operation["tags"], f"{method} {path}"
        assert set(operation["tags"]) <= known, f"{method} {path}"
