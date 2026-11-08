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


def test_openapi_documents_the_customer_export(clients: dict[str, TestClient]) -> None:
    document = clients["sales"].get("/api/openapi.json").json()

    operation = document["paths"]["/api/customers/export"]["get"]
    assert {"200", "401", "422"} <= set(operation["responses"])
    response = operation["responses"]["200"]
    assert response["content"] == {"text/csv": {"schema": {"type": "string"}}}
    assert set(response["headers"]) == {"Content-Disposition", "Cache-Control"}


def test_openapi_documents_the_customer_import(clients: dict[str, TestClient]) -> None:
    document = clients["sales"].get("/api/openapi.json").json()

    operation = document["paths"]["/api/customers/import"]["post"]
    assert {"201", "400", "401", "403", "409", "413", "422"} <= set(operation["responses"])
    assert operation["responses"]["400"]["description"] == (
        "The body is not a valid multipart/form-data body. Code: `BAD_REQUEST`."
    )
    request = operation["requestBody"]
    assert request["required"] is True
    reference = request["content"]["multipart/form-data"]["schema"]["$ref"]
    schema_name = reference.rsplit("/", 1)[-1]
    file_part = document["components"]["schemas"][schema_name]["properties"]["file"]
    assert file_part["type"] == "string"
    assert file_part["format"] == "binary"
    assert (
        "rows[2].email"
        in operation["responses"]["422"]["content"]["application/problem+json"]["examples"][
            "import-errors"
        ]["value"]["errors"][1]["field"]
    )
    assert "column names" in operation["description"].lower()


def test_openapi_documents_the_customer_routes(clients: dict[str, TestClient]) -> None:
    document = clients["sales"].get("/api/openapi.json").json()

    assert "/api/customers" in document["paths"]
    assert "/api/customers/{id}" in document["paths"]
    assert "/api/customers/{id}/deactivate" in document["paths"]
    assert "/api/customers/{id}/reactivate" in document["paths"]
    assert "401" in document["paths"]["/api/customers"]["get"]["responses"]
    assert "409" in document["paths"]["/api/customers/{id}"]["patch"]["responses"]
