"""In-memory implementations of the test-only control stores."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from threading import RLock

from sqlalchemy.engine import Connection

from app.infra.clock import OffsetClock
from app.modules.testcontrols.models import FaultDecision, NewRule, Rule
from app.modules.testcontrols.ports import MAX_FAULT_RULES, TooManyFaultRules


class InMemoryClockOffsetStore:
    """Persist the offset in the application's existing ``OffsetClock``."""

    def __init__(self, clock: OffsetClock) -> None:
        self._clock = clock

    def get(self, *, connection: Connection | None = None) -> float:
        return self._clock.offset.total_seconds()

    def set(self, seconds: float, *, connection: Connection | None = None) -> None:
        self._clock.set_offset(timedelta(seconds=seconds))

    def advance(self, seconds: float, *, connection: Connection | None = None) -> float:
        self._clock.advance(timedelta(seconds=seconds))
        return self.get()


class InMemoryFaultStore:
    """A thread-safe fault store backed by a dictionary."""

    def __init__(self) -> None:
        self._rules: dict[int, Rule] = {}
        self._next_id = 1
        self._lock = RLock()

    def add(self, rule: NewRule) -> Rule:
        with self._lock:
            self._purge_exhausted()
            if len(self._rules) >= MAX_FAULT_RULES:
                raise TooManyFaultRules
            stored = Rule(
                id=self._next_id,
                target=rule.target,
                method=rule.method,
                path=rule.path,
                latency_ms=rule.latency_ms,
                status=rule.status,
                remaining=rule.remaining,
            )
            self._next_id += 1
            self._rules[stored.id] = stored
            return stored

    def list(self) -> list[Rule]:
        with self._lock:
            return [
                rule
                for rule in sorted(self._rules.values(), key=lambda item: item.id)
                if _is_active(rule)
            ]

    def clear(self) -> None:
        with self._lock:
            self._rules.clear()

    def take(
        self,
        method: str,
        path: str,
        *,
        connection: Connection | None = None,
    ) -> FaultDecision | None:
        with self._lock:
            for rule in sorted(self._rules.values(), key=lambda item: item.id):
                if not _is_active(rule) or rule.target != "route":
                    continue
                if rule.method is not None and rule.method != method:
                    continue
                if rule.path != path:
                    continue
                self._rules[rule.id] = _consume(rule)
                return FaultDecision(rule.latency_ms, rule.status)
            return None

    def take_gateway(self, *, connection: Connection | None = None) -> FaultDecision | None:
        with self._lock:
            for rule in sorted(self._rules.values(), key=lambda item: item.id):
                if not _is_active(rule) or rule.target != "gateway":
                    continue
                self._rules[rule.id] = _consume(rule)
                return FaultDecision(rule.latency_ms, rule.status)
            return None

    def _purge_exhausted(self) -> None:
        for rule_id in [rule.id for rule in self._rules.values() if not _is_active(rule)]:
            del self._rules[rule_id]


def _is_active(rule: Rule) -> bool:
    return rule.remaining is None or rule.remaining > 0


def _consume(rule: Rule) -> Rule:
    if rule.remaining is None:
        return rule
    return replace(rule, remaining=rule.remaining - 1)
