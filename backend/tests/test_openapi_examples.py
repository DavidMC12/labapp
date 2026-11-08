"""The named examples of the OpenAPI contract, and the proof that they are true.

The values live in ``app.openapi_examples``: these tests import the same values the
routes publish, send every request example to the seeded in-memory app and validate every
response example against the model of its route.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from app.cli import openapi_document
from app.config import Settings
from app.infra.clock import OffsetClock
from app.main import create_app
from app.modules.auth.seed import DEMO_PASSWORD
from app.modules.customers.schemas import CustomerImportOut, CustomerOut
from app.modules.invoices import schemas as invoice_schemas
from app.modules.orders import schemas as order_schemas
from app.openapi import Problem
from app.openapi_examples import (
    CARD_APPROVED_REQUEST,
    CARD_DECLINED_REQUEST,
    CASH_REQUEST,
    CUSTOMER_CREATE_FULL_REQUEST,
    CUSTOMER_CREATE_MINIMAL_REQUEST,
    CUSTOMER_CREATED_201,
    CUSTOMER_PATCH_REQUEST,
    INVOICE_ISSUED_201,
    LOGIN_REQUEST,
    OPERATION_EXAMPLES,
    ORDER_CREATE_REQUEST,
    ORDER_CREATED_201,
    ORDER_CUSTOMER_PATCH_REQUEST,
    ORDER_LINE_CREATE_REQUEST,
    ORDER_LINE_CREATED_201,
    ORDER_LINE_PATCH_REQUEST,
    PAYMENT_APPROVED_201,
    PAYMENT_DECLINED_402,
    SETTINGS_PATCH_REQUEST,
    TRANSFER_REQUEST,
)
from tests.infra.helpers import FixedClock

FIXED_NOW = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)
SPEC_PATH = Path(__file__).resolve().parents[2] / "docs" / "SPEC.md"

REQUEST_EXAMPLE_KEYS: dict[tuple[str, str], set[str]] = {
    ("post", "/api/auth/login"): {"admin"},
    ("post", "/api/customers"): {"minimal", "full"},
    ("patch", "/api/customers/{id}"): {"update-contact"},
    ("post", "/api/orders"): {"new-draft"},
    ("patch", "/api/orders/{id}"): {"change-customer"},
    ("post", "/api/orders/{id}/lines"): {"add-keyboard"},
    ("patch", "/api/orders/{id}/lines/{line_id}"): {"change-quantity"},
    ("patch", "/api/settings"): {"set-tax-rate"},
    ("post", "/api/invoices/{id}/payments"): {
        "card-approved",
        "card-declined",
        "transfer",
        "cash",
    },
}

RESPONSE_EXAMPLE_KEYS: dict[tuple[str, str, str], set[str]] = {
    ("post", "/api/customers", "201"): {"created"},
    ("post", "/api/orders", "201"): {"created"},
    ("post", "/api/orders/{id}/lines", "201"): {"line-added"},
    ("post", "/api/orders/{id}/invoice", "201"): {"issued"},
    ("post", "/api/invoices/{id}/payments", "201"): {"approved"},
    ("post", "/api/invoices/{id}/payments", "402"): {"declined"},
    ("post", "/api/customers", "409"): {"email-taken"},
    ("post", "/api/customers/import", "201"): {"imported"},
    ("post", "/api/customers/import", "422"): {"import-errors"},
}

COMMON_PROBLEM_EXAMPLES = {
    "401": {"unauthenticated"},
    "403": {"forbidden"},
    "404": {"not-found"},
    "409": {"version-conflict"},
    "422": {"validation-error"},
}

PROBLEM_EXAMPLE_EXCEPTIONS = {
    ("post", "/api/auth/login", "401"): {"invalid-credentials"},
    ("post", "/api/auth/login", "403"): {"origin-mismatch"},
    ("post", "/api/auth/logout", "403"): {"origin-mismatch"},
    ("post", "/api/customers", "409"): {"email-taken"},
    ("post", "/api/customers/import", "409"): {"email-taken"},
    ("post", "/api/customers/import", "422"): {"import-errors"},
}

CODE_IN_DESCRIPTION = re.compile(r"`([A-Z][A-Z0-9_]*)`")

MODELS = {
    "CustomerOut": CustomerOut,
    "CustomerImportOut": CustomerImportOut,
    "Order": order_schemas.Order,
    "Invoice": invoice_schemas.Invoice,
    "PaymentResult": invoice_schemas.PaymentResult,
    "Problem": Problem,
}


def _app() -> tuple[Any, OffsetClock]:
    clock = OffsetClock(FixedClock(FIXED_NOW))
    app = create_app(
        Settings(
            session_secret="test-secret",
            test_mode=False,
            app_origin="http://localhost:3000",
        ),
        clock=clock,
    )
    return app, clock


def _client(app: Any, email: str = "admin@labapp.test") -> TestClient:
    client = TestClient(app)
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    return client


def _json_media(operation: dict[str, Any], media_type: str = "application/json") -> dict[str, Any]:
    return operation.get("requestBody", {}).get("content", {}).get(media_type, {})


def _media_with_examples(response: dict[str, Any]) -> dict[str, Any]:
    for media in response.get("content", {}).values():
        if "examples" in media:
            return media
    return {}


def _schema_name(response: dict[str, Any]) -> str:
    for media in response.get("content", {}).values():
        reference = media.get("schema", {}).get("$ref")
        if isinstance(reference, str):
            return reference.rsplit("/", 1)[-1]
    raise AssertionError(f"response has no schema reference: {response}")


def _spec_section(number: int) -> str:
    text = SPEC_PATH.read_text(encoding="utf-8")
    start = text.index(f"## {number}.")
    end = text.find("\n## ", start + 1)
    return text[start:] if end == -1 else text[start:end]


def test_every_request_body_example_is_named_with_a_summary_and_a_value() -> None:
    contract = openapi_document()

    for path, operations in contract["paths"].items():
        for method, operation in operations.items():
            media = _json_media(operation)
            for name, example in media.get("examples", {}).items():
                assert set(example) == {"summary", "value"}, f"{method} {path} {name}"
                assert example["summary"], f"{method} {path} {name}"


def test_the_request_examples_are_in_the_generated_contract() -> None:
    contract = openapi_document()

    for (method, path), names in REQUEST_EXAMPLE_KEYS.items():
        media = _json_media(contract["paths"][path][method])
        assert set(media.get("examples", {})) == names, f"{method.upper()} {path}"


def test_the_response_examples_are_in_the_generated_contract() -> None:
    contract = openapi_document()

    for (method, path, status), names in RESPONSE_EXAMPLE_KEYS.items():
        response = contract["paths"][path][method]["responses"][status]
        media = _media_with_examples(response)
        assert set(media.get("examples", {})) == names, f"{method.upper()} {path} {status}"


def test_the_contract_carries_every_registered_example_verbatim() -> None:
    contract = openapi_document()

    for (method, path), examples in OPERATION_EXAMPLES.items():
        operation = contract["paths"][path][method.lower()]
        if "request" in examples:
            media = _json_media(operation)
            assert media["examples"] == examples["request"], f"{method} {path} request"
        for status, named_examples in examples.get("responses", {}).items():
            media = _media_with_examples(operation["responses"][status])
            assert media["examples"] == named_examples, f"{method} {path} {status}"


def test_every_common_problem_answer_reuses_the_same_example() -> None:
    contract = openapi_document()

    for path, operations in contract["paths"].items():
        for method, operation in operations.items():
            for status, names in COMMON_PROBLEM_EXAMPLES.items():
                response = operation["responses"].get(status)
                if response is None:
                    continue
                media = _media_with_examples(response)
                expected = PROBLEM_EXAMPLE_EXCEPTIONS.get((method, path, status), names)
                assert set(media.get("examples", {})) == expected, (
                    f"{method.upper()} {path} {status}"
                )


def test_every_problem_example_code_is_named_in_its_response_description() -> None:
    contract = openapi_document()
    checked = 0

    for path, operations in contract["paths"].items():
        for method, operation in operations.items():
            for status, response in operation.get("responses", {}).items():
                if not status.isdigit() or int(status) < 400:
                    continue
                examples = _media_with_examples(response).get("examples", {})
                if not examples:
                    continue
                named_codes = set(CODE_IN_DESCRIPTION.findall(response["description"]))
                assert named_codes, f"{method.upper()} {path} {status} names no code"
                for name, example in examples.items():
                    assert example["value"]["code"] in named_codes, (
                        f"{method.upper()} {path} {status} {name}: "
                        f"{example['value']['code']} is not one of {sorted(named_codes)}"
                    )
                    checked += 1
    assert checked


def test_every_response_example_validates_against_its_response_model() -> None:
    contract = openapi_document()

    for path, operations in contract["paths"].items():
        for method, operation in operations.items():
            for status, response in operation.get("responses", {}).items():
                for media in response.get("content", {}).values():
                    for name, example in media.get("examples", {}).items():
                        schema_name = _schema_name(response)
                        assert schema_name in MODELS, (
                            f"{method.upper()} {path} {status} {name}: unknown model {schema_name}"
                        )
                        TypeAdapter(MODELS[schema_name]).validate_python(example["value"])


def test_the_login_example_starts_the_admin_session() -> None:
    app, _ = _app()

    response = TestClient(app).post("/api/auth/login", json=LOGIN_REQUEST)

    assert response.status_code == 200
    assert response.json()["email"] == LOGIN_REQUEST["email"]


@pytest.mark.parametrize(
    "body",
    [CUSTOMER_CREATE_MINIMAL_REQUEST, CUSTOMER_CREATE_FULL_REQUEST],
    ids=["minimal", "full"],
)
def test_the_customer_create_examples_are_accepted(body: dict[str, Any]) -> None:
    app, _ = _app()
    client = _client(app)

    response = client.post("/api/customers", json=body)

    assert response.status_code == 201
    if body is CUSTOMER_CREATE_FULL_REQUEST:
        assert response.json() == CUSTOMER_CREATED_201


def test_the_customer_patch_example_is_accepted() -> None:
    app, _ = _app()
    client = _client(app)

    response = client.patch("/api/customers/1", json=CUSTOMER_PATCH_REQUEST)

    assert response.status_code == 200


def test_the_order_create_example_returns_the_documented_draft() -> None:
    app, _ = _app()
    client = _client(app, "sales@labapp.test")

    response = client.post("/api/orders", json=ORDER_CREATE_REQUEST)

    assert response.status_code == 201
    assert response.json() == ORDER_CREATED_201


def test_the_order_customer_patch_example_is_accepted() -> None:
    app, _ = _app()
    client = _client(app, "sales@labapp.test")
    assert client.post("/api/orders", json=ORDER_CREATE_REQUEST).status_code == 201

    response = client.patch("/api/orders/8", json=ORDER_CUSTOMER_PATCH_REQUEST)

    assert response.status_code == 200
    assert response.json()["customer"]["id"] == ORDER_CUSTOMER_PATCH_REQUEST["customer_id"]


def test_the_order_line_create_example_returns_the_documented_line() -> None:
    app, clock = _app()
    client = _client(app, "sales@labapp.test")
    assert client.post("/api/orders", json=ORDER_CREATE_REQUEST).status_code == 201
    clock.advance(timedelta(minutes=1))

    response = client.post("/api/orders/8/lines", json=ORDER_LINE_CREATE_REQUEST)

    assert response.status_code == 201
    assert response.json() == ORDER_LINE_CREATED_201


def test_the_order_line_patch_example_is_accepted() -> None:
    app, _ = _app()
    client = _client(app, "sales@labapp.test")

    response = client.patch("/api/orders/1/lines/1", json=ORDER_LINE_PATCH_REQUEST)

    assert response.status_code == 200
    assert response.json()["lines"][0]["quantity"] == ORDER_LINE_PATCH_REQUEST["quantity"]


def test_the_settings_patch_example_is_accepted() -> None:
    app, _ = _app()
    client = _client(app)

    response = client.patch("/api/settings", json=SETTINGS_PATCH_REQUEST)

    assert response.status_code == 200
    assert response.json() == {"tax_rate": "12.50"}


def test_the_card_approved_example_reproduces_the_spec_six_examples() -> None:
    app, clock = _app()
    client = _client(app, "finance@labapp.test")

    issued = client.post("/api/orders/2/invoice")
    assert issued.status_code == 201
    assert issued.json() == INVOICE_ISSUED_201

    clock.advance(timedelta(minutes=2))
    payment = client.post(
        "/api/invoices/4/payments",
        json=CARD_APPROVED_REQUEST,
        headers={"Idempotency-Key": "pay-0001"},
    )

    assert payment.status_code == 201
    assert payment.json() == PAYMENT_APPROVED_201


def test_the_card_declined_example_returns_the_documented_problem() -> None:
    app, _ = _app()
    client = _client(app, "finance@labapp.test")

    response = client.post(
        "/api/invoices/1/payments",
        json=CARD_DECLINED_REQUEST,
        headers={"Idempotency-Key": "pay-0002"},
    )

    assert response.status_code == 402
    assert response.json() == PAYMENT_DECLINED_402


@pytest.mark.parametrize(
    ("body", "key"),
    [(TRANSFER_REQUEST, "pay-transfer"), (CASH_REQUEST, "pay-cash")],
    ids=["transfer", "cash"],
)
def test_the_transfer_and_cash_examples_are_approved(body: dict[str, Any], key: str) -> None:
    app, _ = _app()
    client = _client(app, "finance@labapp.test")

    response = client.post(
        "/api/invoices/1/payments",
        json=body,
        headers={"Idempotency-Key": key},
    )

    assert response.status_code == 201
    assert response.json()["payment"]["status"] == "approved"


def test_the_payment_examples_equal_the_spec_six_payloads() -> None:
    section = _spec_section(6)
    blocks = [json.loads(block) for block in re.findall(r"```json\n(.*?)```", section, re.S)]
    inline = [
        json.loads(match.group(1))
        for match in re.finditer(r"`(\{[^`]*\"method\"[^`]*\})`", section)
    ]

    assert inline == [CARD_APPROVED_REQUEST, CARD_DECLINED_REQUEST]
    assert len(blocks) == 3
    assert INVOICE_ISSUED_201 == blocks[0]
    assert PAYMENT_APPROVED_201 == blocks[1]
    assert PAYMENT_DECLINED_402 == blocks[2]
