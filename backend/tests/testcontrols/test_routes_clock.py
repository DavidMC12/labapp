"""The clock endpoints of the test-only controls."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.infra.clock import OffsetClock
from app.main import create_app
from app.modules.testcontrols.ports import MAX_CLOCK_OFFSET_SECONDS

NOW = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)


class FixedClock:
    """A base clock that never moves."""

    def now(self) -> datetime:
        return NOW


def _fixed_client() -> TestClient:
    app = create_app(
        Settings(session_secret="test-secret", test_mode=True),
        clock=OffsetClock(FixedClock()),
    )
    return TestClient(app)


def test_get_returns_the_application_time_and_the_offset(
    controls_client: TestClient,
) -> None:
    response = controls_client.get("/__test__/clock")

    assert response.status_code == 200
    body = response.json()
    assert body["offset_seconds"] == 0.0
    assert body["now"].endswith("Z")
    parsed = datetime.fromisoformat(body["now"].replace("Z", "+00:00"))
    assert parsed.tzinfo == UTC


def test_setting_the_offset_moves_the_answer() -> None:
    client = _fixed_client()

    response = client.post("/__test__/clock", json={"offset_seconds": 3600})

    assert response.status_code == 200
    assert response.json()["offset_seconds"] == 3600.0
    assert response.json()["now"] == "2026-02-01T13:00:00Z"
    assert client.get("/__test__/clock").json()["now"] == "2026-02-01T13:00:00Z"


def test_advancing_adds_to_the_current_offset() -> None:
    client = _fixed_client()

    assert client.post("/__test__/clock", json={"offset_seconds": 3600}).status_code == 200
    response = client.post("/__test__/clock", json={"advance_seconds": 90.5})

    assert response.status_code == 200
    assert response.json()["offset_seconds"] == pytest.approx(3690.5)
    assert response.json()["now"] == "2026-02-01T13:01:30.500000Z"


def test_the_offset_boundary_is_inclusive() -> None:
    client = _fixed_client()

    response = client.post(
        "/__test__/clock",
        json={"offset_seconds": MAX_CLOCK_OFFSET_SECONDS},
    )

    assert response.status_code == 200
    assert response.json()["offset_seconds"] == MAX_CLOCK_OFFSET_SECONDS


def test_an_offset_beyond_the_boundary_is_a_validation_error() -> None:
    client = _fixed_client()

    response = client.post(
        "/__test__/clock",
        json={"offset_seconds": MAX_CLOCK_OFFSET_SECONDS + 1},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["errors"] == [
        {
            "field": "offset_seconds",
            "code": "OUT_OF_RANGE",
            "message": (
                f"El valor debe estar entre {-int(MAX_CLOCK_OFFSET_SECONDS)} "
                f"y {int(MAX_CLOCK_OFFSET_SECONDS)}."
            ),
        }
    ]


def test_an_advance_that_leaves_the_range_is_refused_without_changing_it() -> None:
    client = _fixed_client()
    client.post("/__test__/clock", json={"offset_seconds": MAX_CLOCK_OFFSET_SECONDS})

    response = client.post("/__test__/clock", json={"advance_seconds": 1})

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "advance_seconds"
    assert response.json()["errors"][0]["code"] == "OUT_OF_RANGE"
    assert client.get("/__test__/clock").json()["offset_seconds"] == MAX_CLOCK_OFFSET_SECONDS


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"offset_seconds": 1, "advance_seconds": 1},
        {"offset_seconds": None, "advance_seconds": None},
        {"offset_seconds": "1"},
        {"offset_seconds": True},
        {"advance_seconds": False},
        {"offset_seconds": 1, "unknown": 2},
    ],
)
def test_invalid_clock_bodies_are_validation_errors(
    controls_client: TestClient,
    body: dict[str, object],
) -> None:
    response = controls_client.post("/__test__/clock", json=body)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    "payload",
    [
        b'{"offset_seconds": 1e999}',
        b'{"offset_seconds": NaN}',
        b'{"advance_seconds": -1e999}',
        b'{"advance_seconds": Infinity}',
    ],
)
def test_non_finite_numbers_are_validation_errors(
    controls_client: TestClient,
    payload: bytes,
) -> None:
    response = controls_client.post(
        "/__test__/clock",
        content=payload,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_a_missing_body_is_a_validation_error(controls_client: TestClient) -> None:
    response = controls_client.post("/__test__/clock")

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_the_clock_does_not_need_a_session(controls_client: TestClient) -> None:
    response = controls_client.post(
        "/__test__/clock",
        json={"offset_seconds": 60},
    )

    assert response.status_code == 200
    assert response.json()["offset_seconds"] == 60.0
