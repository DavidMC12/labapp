"""Tests for the order OpenAPI document."""

from __future__ import annotations

from fastapi.testclient import TestClient

MONEY_FIELDS = {
    "Product": ["price"],
    "OrderLine": ["unit_price", "line_total"],
    "Order": ["subtotal", "tax_rate", "tax", "total"],
    "OrderSummary": ["total"],
    "TaxRateOut": ["tax_rate"],
}


def test_openapi_contains_the_order_schemas(clients: dict[str, TestClient]) -> None:
    document = clients["sales"].get("/api/openapi.json").json()

    schemas = document["components"]["schemas"]
    for name in ("Order", "OrderSummary", "OrderLine", "Product"):
        assert name in schemas


def test_every_money_field_is_a_string(clients: dict[str, TestClient]) -> None:
    schemas = clients["sales"].get("/api/openapi.json").json()["components"]["schemas"]

    for schema_name, fields in MONEY_FIELDS.items():
        for field in fields:
            assert schemas[schema_name]["properties"][field]["type"] == "string", (
                schema_name,
                field,
            )


def test_openapi_documents_the_order_export(clients: dict[str, TestClient]) -> None:
    document = clients["sales"].get("/api/openapi.json").json()

    operation = document["paths"]["/api/orders/export"]["get"]
    assert {"200", "401", "422"} <= set(operation["responses"])
    response = operation["responses"]["200"]
    assert response["content"] == {"text/csv": {"schema": {"type": "string"}}}
    assert set(response["headers"]) == {"Content-Disposition", "Cache-Control"}


def test_openapi_documents_the_order_routes(clients: dict[str, TestClient]) -> None:
    document = clients["sales"].get("/api/openapi.json").json()

    for path in (
        "/api/products",
        "/api/settings",
        "/api/orders",
        "/api/orders/{id}",
        "/api/orders/{id}/lines",
        "/api/orders/{id}/lines/{line_id}",
        "/api/orders/{id}/confirm",
        "/api/orders/{id}/cancel",
        "/api/orders/{id}/ship",
    ):
        assert path in document["paths"]
