"""Tests for the customer OpenAPI document."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_openapi_contains_the_customer_schemas(clients: dict[str, TestClient]) -> None:
    document = clients["sales"].get("/api/openapi.json").json()

    schemas = document["components"]["schemas"]
    assert "CustomerOut" in schemas
    assert "CustomerListOut" in schemas
    assert "CustomerCreate" in schemas
    assert "CustomerPatch" in schemas


def test_openapi_documents_the_customer_routes(clients: dict[str, TestClient]) -> None:
    document = clients["sales"].get("/api/openapi.json").json()

    assert "/api/customers" in document["paths"]
    assert "/api/customers/{id}" in document["paths"]
    assert "/api/customers/{id}/deactivate" in document["paths"]
    assert "/api/customers/{id}/reactivate" in document["paths"]
    assert "401" in document["paths"]["/api/customers"]["get"]["responses"]
    assert "409" in document["paths"]["/api/customers/{id}"]["patch"]["responses"]
