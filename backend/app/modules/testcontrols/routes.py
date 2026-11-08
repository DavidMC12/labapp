"""HTTP endpoints for the test-only controls."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.exc import IntegrityError

from app.errors import ERROR_MESSAGES, NOT_FOUND, VALIDATION_ERROR, ApiError
from app.modules.testcontrols.models import NewRule, Rule
from app.modules.testcontrols.ports import MAX_CLOCK_OFFSET_SECONDS, TooManyFaultRules
from app.modules.testcontrols.reset import (
    RESET_CONFLICT,
    RESET_CONFLICT_DETAIL,
    Dataset,
)
from app.modules.testcontrols.validation import validate_rule
from app.security.controls_guard import controls_allowed

MAX_FAULT_TIMES = 1_000


def require_controls(
    request: Request,
    x_test_token: Annotated[str | None, Header(alias="X-Test-Token")] = None,
) -> None:
    """Repeat the controls guard inside the router, as a second layer."""
    settings = request.app.state.settings
    if not controls_allowed(settings.test_mode, settings.test_token, x_test_token):
        raise ApiError(404, NOT_FOUND, ERROR_MESSAGES[NOT_FOUND])


router = APIRouter(
    prefix="/__test__",
    include_in_schema=False,
    dependencies=[Depends(require_controls)],
)


class SeedBody(BaseModel):
    """The dataset to load."""

    model_config = ConfigDict(extra="forbid", strict=True)

    dataset: Dataset


class ClockBody(BaseModel):
    """Exactly one of a replacement offset or an advance."""

    model_config = ConfigDict(extra="forbid", strict=True)

    offset_seconds: float | None = Field(default=None, allow_inf_nan=False)
    advance_seconds: float | None = Field(default=None, allow_inf_nan=False)

    @model_validator(mode="after")
    def _exactly_one(self) -> ClockBody:
        if (self.offset_seconds is None) == (self.advance_seconds is None):
            raise ValueError("Send exactly one of offset_seconds or advance_seconds")
        return self


class FaultBody(BaseModel):
    """The payload of a new fault rule; the rule validation checks the values."""

    model_config = ConfigDict(extra="forbid", strict=True)

    target: str
    method: str | None = None
    path: str | None = None
    latency_ms: int = 0
    status: int | None = None
    times: int | None = None


def _validation_error(field: str, code: str, message: str) -> ApiError:
    return ApiError(
        422,
        VALIDATION_ERROR,
        ERROR_MESSAGES[VALIDATION_ERROR],
        errors=[{"field": field, "code": code, "message": message}],
    )


def _outside_the_clock_range(field: str) -> ApiError:
    limit = int(MAX_CLOCK_OFFSET_SECONDS)
    return _validation_error(
        field,
        "OUT_OF_RANGE",
        f"El valor debe estar entre {-limit} y {limit}.",
    )


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _clock_out(request: Request) -> dict[str, object]:
    return {
        "now": _iso(request.app.state.container.clock.now()),
        "offset_seconds": request.app.state.clock_store.get(),
    }


def _rule_out(rule: Rule) -> dict[str, object]:
    return {
        "id": rule.id,
        "target": rule.target,
        "method": rule.method,
        "path": rule.path,
        "latency_ms": rule.latency_ms,
        "status": rule.status,
        "remaining": rule.remaining,
    }


@router.post("/reset")
def reset(request: Request) -> dict[str, str]:
    """Restore the demo data, the sequences, the clock and the faults."""
    try:
        request.app.state.resetter.reset()
    except IntegrityError as error:
        raise ApiError(409, RESET_CONFLICT, RESET_CONFLICT_DETAIL) from error
    return {"status": "ok"}


@router.post("/seed")
def seed(payload: SeedBody, request: Request) -> dict[str, str]:
    """Load the ``default`` data or leave only the users and the settings."""
    request.app.state.resetter.seed(payload.dataset)
    return {"dataset": payload.dataset}


@router.get("/clock")
def read_clock(request: Request) -> dict[str, object]:
    """Return the application time and the stored offset."""
    return _clock_out(request)


@router.post("/clock")
def change_clock(payload: ClockBody, request: Request) -> dict[str, object]:
    """Replace the offset or advance it, keeping it inside plus or minus ten years."""
    store = request.app.state.clock_store
    if payload.offset_seconds is not None:
        if abs(payload.offset_seconds) > MAX_CLOCK_OFFSET_SECONDS:
            raise _outside_the_clock_range("offset_seconds")
        store.set(payload.offset_seconds)
    else:
        delta = payload.advance_seconds
        assert delta is not None
        if store.advance(delta, limit=MAX_CLOCK_OFFSET_SECONDS) is None:
            raise _outside_the_clock_range("advance_seconds")
    return _clock_out(request)


@router.post("/faults", status_code=status.HTTP_201_CREATED)
def add_fault(payload: FaultBody, request: Request) -> dict[str, object]:
    """Add a fault rule and return it with its id."""
    if payload.times is not None and not 1 <= payload.times <= MAX_FAULT_TIMES:
        raise _validation_error(
            "times",
            "OUT_OF_RANGE",
            f"El valor debe estar entre 1 y {MAX_FAULT_TIMES}.",
        )

    rule = NewRule(
        target=payload.target,
        method=payload.method,
        path=payload.path,
        latency_ms=payload.latency_ms,
        status=payload.status,
        remaining=payload.times,
    )
    validate_rule(rule)
    try:
        stored = request.app.state.fault_store.add(rule)
    except TooManyFaultRules as error:
        raise ApiError(
            422,
            VALIDATION_ERROR,
            ERROR_MESSAGES[VALIDATION_ERROR],
        ) from error
    return _rule_out(stored)


@router.get("/faults")
def list_faults(request: Request) -> list[dict[str, object]]:
    """List the non-exhausted rules with their remaining count."""
    return [_rule_out(rule) for rule in request.app.state.fault_store.list()]


@router.delete("/faults", status_code=status.HTTP_204_NO_CONTENT)
def clear_faults(request: Request) -> Response:
    """Remove every fault rule."""
    request.app.state.fault_store.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = [
    "ClockBody",
    "FaultBody",
    "SeedBody",
    "require_controls",
    "router",
]
