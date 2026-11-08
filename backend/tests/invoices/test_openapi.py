"""Tests for the invoice OpenAPI document."""

from __future__ import annotations

from fastapi.testclient import TestClient

MONEY_FIELDS = {
    "Invoice": ["subtotal", "tax_rate", "tax", "total"],
    "InvoiceLine": ["unit_price", "line_total"],
    "InvoiceSummary": ["total"],
    "Payment": ["amount"],
}


def test_openapi_contains_the_invoice_schemas(clients: dict[str, TestClient]) -> None:
    document = clients["finance"].get("/api/openapi.json").json()

    schemas = document["components"]["schemas"]
    for name in ("Invoice", "InvoiceSummary", "Payment", "PaymentResult"):
        assert name in schemas


def test_every_invoice_money_field_is_a_string(clients: dict[str, TestClient]) -> None:
    schemas = clients["finance"].get("/api/openapi.json").json()["components"]["schemas"]

    for schema_name, fields in MONEY_FIELDS.items():
        for field in fields:
            assert schemas[schema_name]["properties"][field]["type"] == "string", (
                schema_name,
                field,
            )


def test_openapi_documents_the_invoice_routes(clients: dict[str, TestClient]) -> None:
    document = clients["finance"].get("/api/openapi.json").json()

    for path in (
        "/api/invoices",
        "/api/invoices/{id}",
        "/api/orders/{id}/invoice",
        "/api/invoices/{id}/payments",
    ):
        assert path in document["paths"]
