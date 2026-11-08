"""Models returned by the test-only controls."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NewRule:
    """A fault rule before the store assigns its id."""

    target: str
    method: str | None = None
    path: str | None = None
    latency_ms: int = 0
    status: int | None = None
    remaining: int | None = None


@dataclass(frozen=True)
class Rule:
    """A stored fault rule.

    ``remaining`` is ``None`` until the rule is removed; a rule at 0 is exhausted
    and ignored by every read.
    """

    id: int
    target: str
    method: str | None
    path: str | None
    latency_ms: int
    status: int | None
    remaining: int | None


@dataclass(frozen=True)
class FaultDecision:
    """What one request or gateway call must do."""

    latency_ms: int
    status: int | None
