"""Validation of the fault rules used by the controls endpoints."""

from __future__ import annotations

import pytest

from app.errors import ApiError
from app.modules.testcontrols.models import NewRule
from app.modules.testcontrols.validation import validate_rule


def _route(**overrides: object) -> NewRule:
    values: dict[str, object] = {
        "target": "route",
        "method": "GET",
        "path": "/api/orders",
        "latency_ms": 0,
        "status": 500,
        "remaining": None,
    }
    values.update(overrides)
    return NewRule(**values)  # type: ignore[arg-type]


def _gateway(**overrides: object) -> NewRule:
    values: dict[str, object] = {"target": "gateway", "remaining": 1}
    values.update(overrides)
    return NewRule(**values)  # type: ignore[arg-type]


def test_a_route_with_latency_is_valid() -> None:
    validate_rule(_route(latency_ms=250, status=None))


def test_a_route_with_a_status_is_valid() -> None:
    validate_rule(_route(latency_ms=0, status=418))


def test_a_route_needs_a_latency_or_a_status() -> None:
    with pytest.raises(ApiError) as info:
        validate_rule(_route(latency_ms=0, status=None))

    assert info.value.code == "VALIDATION_ERROR"
    assert info.value.errors == [
        {
            "field": "latency_ms",
            "code": "INVALID_FORMAT",
            "message": "La regla necesita latencia o un estado.",
        }
    ]


def test_a_route_needs_a_path_that_starts_with_a_slash() -> None:
    with pytest.raises(ApiError) as missing:
        validate_rule(_route(path=None))
    assert missing.value.errors == [
        {"field": "path", "code": "REQUIRED", "message": "Este campo es obligatorio."}
    ]

    with pytest.raises(ApiError) as no_slash:
        validate_rule(_route(path="api/orders"))
    assert no_slash.value.errors == [
        {
            "field": "path",
            "code": "INVALID_FORMAT",
            "message": "El formato no es válido.",
        }
    ]


def test_a_gateway_rule_accepts_only_its_own_fields() -> None:
    validate_rule(_gateway())

    with pytest.raises(ApiError) as info:
        validate_rule(_gateway(method="GET", path="/api/orders", status=500))

    assert [(error["field"], error["code"]) for error in info.value.errors or []] == [
        ("method", "INVALID_FORMAT"),
        ("path", "INVALID_FORMAT"),
        ("status", "INVALID_FORMAT"),
    ]


def test_the_ranges_are_checked() -> None:
    with pytest.raises(ApiError) as info:
        validate_rule(_route(latency_ms=10_001, status=399, remaining=-1))

    assert [(error["field"], error["code"]) for error in info.value.errors or []] == [
        ("latency_ms", "OUT_OF_RANGE"),
        ("status", "OUT_OF_RANGE"),
        ("remaining", "OUT_OF_RANGE"),
    ]


def test_an_unknown_target_is_rejected() -> None:
    with pytest.raises(ApiError) as info:
        validate_rule(NewRule(target="database"))

    assert info.value.errors == [
        {
            "field": "target",
            "code": "INVALID_FORMAT",
            "message": "El formato no es válido.",
        }
    ]
