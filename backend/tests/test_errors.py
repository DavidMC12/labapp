from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.errors import ApiError

MAX_BODY_BYTES = 100 * 1024


class Line(BaseModel):
    quantity: int


class OrderPayload(BaseModel):
    customer_id: int
    lines: list[Line]


def _assert_problem(
    response: Any,
    *,
    status: int,
    code: str,
    detail: str,
) -> dict[str, Any]:
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["x-request-id"]

    body = response.json()
    assert body["type"] == "about:blank"
    assert body["title"]
    assert body["status"] == status
    assert body["code"] == code
    assert body["detail"] == detail
    return body


def test_unknown_route_returns_not_found(client: TestClient) -> None:
    response = client.get("/no-such-route")

    _assert_problem(
        response,
        status=404,
        code="NOT_FOUND",
        detail="No se encontró el recurso solicitado.",
    )


def test_method_not_allowed_uses_the_spanish_detail(client: TestClient) -> None:
    response = client.post("/api/health")

    _assert_problem(
        response,
        status=405,
        code="METHOD_NOT_ALLOWED",
        detail="Método no permitido para este recurso.",
    )


def test_status_outside_the_table_uses_the_default_spanish_detail(app: FastAPI) -> None:
    @app.get("/teapot")
    def teapot() -> None:
        raise HTTPException(status_code=418, detail="I'm a teapot")

    response = TestClient(app).get("/teapot")

    body = _assert_problem(
        response,
        status=418,
        code="IM_A_TEAPOT",
        detail="No se pudo completar la solicitud.",
    )
    assert body["title"] == "I'm a Teapot"
    assert "teapot" not in body["detail"]


def test_error_response_echoes_request_id(client: TestClient) -> None:
    response = client.get("/no-such-route", headers={"X-Request-Id": "req-42"})

    assert response.headers["x-request-id"] == "req-42"


def test_payload_too_large_returns_413(client: TestClient) -> None:
    response = client.post("/api/health", content=b"x" * (MAX_BODY_BYTES + 1))

    _assert_problem(
        response,
        status=413,
        code="PAYLOAD_TOO_LARGE",
        detail="La solicitud es demasiado grande.",
    )


def test_body_at_the_limit_is_allowed(app: FastAPI) -> None:
    @app.post("/echo")
    async def echo(request: Request) -> dict[str, int]:
        return {"size": len(await request.body())}

    response = TestClient(app).post("/echo", content=b"x" * MAX_BODY_BYTES)

    assert response.status_code == 200
    assert response.json() == {"size": MAX_BODY_BYTES}


def test_validation_error_lists_missing_fields(app: FastAPI) -> None:
    @app.post("/orders")
    def create_order(payload: OrderPayload) -> OrderPayload:
        return payload

    response = TestClient(app).post("/orders", json={})

    body = _assert_problem(
        response,
        status=422,
        code="VALIDATION_ERROR",
        detail="Revisa los datos ingresados.",
    )
    assert body["errors"] == [
        {
            "field": "customer_id",
            "code": "REQUIRED",
            "message": "Este campo es obligatorio.",
        },
        {
            "field": "lines",
            "code": "REQUIRED",
            "message": "Este campo es obligatorio.",
        },
    ]


def test_validation_error_uses_nested_field_paths_and_invalid_format(app: FastAPI) -> None:
    @app.post("/orders")
    def create_order(payload: OrderPayload) -> OrderPayload:
        return payload

    response = TestClient(app).post(
        "/orders",
        json={"customer_id": 1, "lines": [{"quantity": "many"}]},
    )

    body = _assert_problem(
        response,
        status=422,
        code="VALIDATION_ERROR",
        detail="Revisa los datos ingresados.",
    )
    assert body["errors"] == [
        {
            "field": "lines[0].quantity",
            "code": "INVALID_FORMAT",
            "message": "El formato no es válido.",
        }
    ]


def test_unhandled_error_returns_internal_error(app: FastAPI) -> None:
    @app.get("/explode")
    def explode() -> None:
        raise RuntimeError("database password is hunter2")

    response = TestClient(app, raise_server_exceptions=False).get("/explode")

    body = _assert_problem(
        response,
        status=500,
        code="INTERNAL_ERROR",
        detail="Ocurrió un error inesperado. Inténtalo de nuevo.",
    )
    assert "hunter2" not in response.text
    assert set(body) == {"type", "title", "status", "code", "detail"}


def test_api_error_renders_errors_and_extra_members(app: FastAPI) -> None:
    @app.get("/conflict")
    def conflict() -> None:
        raise ApiError(
            409,
            "ORDER_NOT_CONFIRMED",
            "Solo se puede facturar un pedido confirmado.",
            errors=[
                {
                    "field": "status",
                    "code": "INVALID_FORMAT",
                    "message": "El formato no es válido.",
                }
            ],
            version=7,
        )

    response = TestClient(app).get("/conflict")

    body = _assert_problem(
        response,
        status=409,
        code="ORDER_NOT_CONFIRMED",
        detail="Solo se puede facturar un pedido confirmado.",
    )
    assert body["version"] == 7
    assert body["errors"] == [
        {
            "field": "status",
            "code": "INVALID_FORMAT",
            "message": "El formato no es válido.",
        }
    ]
