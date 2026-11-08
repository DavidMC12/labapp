"""Storage ports for the application clock offset and the fault rules."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.engine import Connection

from app.modules.testcontrols.models import FaultDecision, NewRule, Rule

MAX_FAULT_RULES = 50


class TooManyFaultRules(Exception):
    """Adding the rule would leave more than 50 non-exhausted rules."""


class ClockOffsetStore(Protocol):
    """The persisted offset of the application clock, in seconds.

    ``connection`` is optional so the request controls middleware can read the offset
    and consume a fault in the same database transaction.
    """

    def get(self, *, connection: Connection | None = None) -> float:
        """Return the stored offset, or ``0.0`` when there is no row."""
        ...

    def set(self, seconds: float, *, connection: Connection | None = None) -> None:
        """Replace the stored offset."""
        ...

    def advance(self, seconds: float, *, connection: Connection | None = None) -> float:
        """Add ``seconds`` atomically and return the new offset."""
        ...


class FaultStore(Protocol):
    """The fault rules shared by every application instance.

    ``add`` and the two ``take`` methods are atomic. ``add`` deletes exhausted rows,
    then inserts only when fewer than 50 non-exhausted rules remain. ``take`` and
    ``take_gateway`` consume the first matching rule with one statement, so under N
    concurrent requests exactly ``remaining`` of them get a decision.
    """

    def add(self, rule: NewRule) -> Rule:
        """Store a rule, deleting exhausted rows first.

        Raises ``TooManyFaultRules`` when 50 non-exhausted rules already exist.
        """
        ...

    def list(self) -> list[Rule]:
        """Return the non-exhausted rules ordered by id."""
        ...

    def clear(self) -> None:
        """Delete every rule."""
        ...

    def take(
        self,
        method: str,
        path: str,
        *,
        connection: Connection | None = None,
    ) -> FaultDecision | None:
        """Consume the first matching ``route`` rule and return its decision."""
        ...

    def take_gateway(self, *, connection: Connection | None = None) -> FaultDecision | None:
        """Consume the first non-exhausted ``gateway`` rule."""
        ...
