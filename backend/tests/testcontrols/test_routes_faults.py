"""The fault endpoints of the test-only controls."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.modules.testcontrols.ports import MAX_FAULT_RULES


def _route(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "target": "route",
        "method": "GET",
        "path": "/api/customers",
        "latency_ms": 0,
        "status": 500,
        "times": None,
    }
    body.update(overrides)
    return body


def test_a_route_rule_is_stored_with_its_id(controls_client: TestClient) -> None:
    response = controls_client.post("/__test__/faults", json=_route(times=2))

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "target": "route",
        "method": "GET",
        "path": "/api/customers",
        "latency_ms": 0,
        "status": 500,
        "remaining": 2,
    }


def test_a_route_with_any_method_and_a_latency_only_is_valid(
    controls_client: TestClient,
) -> None:
    response = controls_client.post(
        "/__test__/faults",
        json={"target": "route", "method": None, "path": "/api/customers", "latency_ms": 250},
    )

    assert response.status_code == 201
    assert response.json()["method"] is None
    assert response.json()["status"] is None


def test_a_gateway_rule_needs_only_its_target(controls_client: TestClient) -> None:
    response = controls_client.post(
        "/__test__/faults",
        json={"target": "gateway", "times": 1},
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "target": "gateway",
        "method": None,
        "path": None,
        "latency_ms": 0,
        "status": None,
        "remaining": 1,
    }


@pytest.mark.parametrize(
    "body",
    [
        _route(latency_ms=10_000, status=None),
        _route(latency_ms=0, status=400),
        _route(latency_ms=0, status=599),
        _route(method="DELETE", times=1),
        _route(times=1_000),
    ],
)
def test_the_boundaries_are_valid(
    controls_client: TestClient,
    body: dict[str, object],
) -> None:
    response = controls_client.post("/__test__/faults", json=body)

    assert response.status_code == 201


@pytest.mark.parametrize(
    ("body", "field", "code"),
    [
        ({"target": "database"}, "target", "INVALID_FORMAT"),
        ({"target": "route", "path": "/api/x"}, "latency_ms", "INVALID_FORMAT"),
        ({"target": "route", "path": "api/x", "status": 500}, "path", "INVALID_FORMAT"),
        (_route(method="OPTIONS"), "method", "INVALID_FORMAT"),
        (_route(latency_ms=-1), "latency_ms", "OUT_OF_RANGE"),
        (_route(latency_ms=10_001), "latency_ms", "OUT_OF_RANGE"),
        (_route(status=399), "status", "OUT_OF_RANGE"),
        (_route(status=600), "status", "OUT_OF_RANGE"),
        (_route(times=0), "times", "OUT_OF_RANGE"),
        (_route(times=1_001), "times", "OUT_OF_RANGE"),
        (_route(latency_ms=True), "latency_ms", "INVALID_FORMAT"),
        (_route(times=True), "times", "INVALID_FORMAT"),
        (_route(latency_ms=1.5), "latency_ms", "INVALID_FORMAT"),
        (
            {"target": "gateway", "method": "GET", "path": "/x", "status": 500},
            "method",
            "INVALID_FORMAT",
        ),
    ],
)
def test_invalid_rules_name_the_offending_field(
    controls_client: TestClient,
    body: dict[str, object],
    field: str,
    code: str,
) -> None:
    response = controls_client.post("/__test__/faults", json=body)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    fields = {(error["field"], error["code"]) for error in response.json()["errors"]}
    assert (field, code) in fields


def test_an_unknown_field_is_refused(controls_client: TestClient) -> None:
    response = controls_client.post(
        "/__test__/faults",
        json={**_route(), "unknown": 1},
    )

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "unknown"


def test_the_list_and_the_delete(controls_client: TestClient) -> None:
    controls_client.post("/__test__/faults", json=_route(path="/api/customers"))
    controls_client.post("/__test__/faults", json={"target": "gateway", "times": 3})

    response = controls_client.get("/__test__/faults")

    assert response.status_code == 200
    assert [(rule["id"], rule["target"]) for rule in response.json()] == [
        (1, "route"),
        (2, "gateway"),
    ]

    assert controls_client.delete("/__test__/faults").status_code == 204
    assert controls_client.get("/__test__/faults").json() == []


def test_the_fifty_first_rule_is_a_validation_error(controls_client: TestClient) -> None:
    for index in range(MAX_FAULT_RULES):
        response = controls_client.post(
            "/__test__/faults",
            json=_route(path=f"/api/{index}"),
        )
        assert response.status_code == 201

    response = controls_client.post("/__test__/faults", json=_route(path="/api/too-many"))

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert len(controls_client.get("/__test__/faults").json()) == MAX_FAULT_RULES
