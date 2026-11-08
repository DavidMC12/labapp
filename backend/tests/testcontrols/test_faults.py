"""The in-memory fault store and its matching rules."""

from __future__ import annotations

import pytest

from app.modules.testcontrols.memory import InMemoryFaultStore
from app.modules.testcontrols.models import FaultDecision, NewRule
from app.modules.testcontrols.ports import MAX_FAULT_RULES, TooManyFaultRules


def _route(
    *,
    method: str | None = "GET",
    path: str = "/api/orders",
    latency_ms: int = 0,
    status: int | None = 500,
    remaining: int | None = None,
) -> NewRule:
    return NewRule(
        target="route",
        method=method,
        path=path,
        latency_ms=latency_ms,
        status=status,
        remaining=remaining,
    )


def test_add_returns_the_stored_rule_and_list_orders_by_id() -> None:
    store = InMemoryFaultStore()

    first = store.add(_route())
    second = store.add(_route(path="/api/invoices"))

    assert first.id == 1
    assert second.id == 2
    assert store.list() == [first, second]


def test_take_matches_the_method_the_exact_path_and_the_first_rule() -> None:
    store = InMemoryFaultStore()
    first = store.add(_route())
    any_method = store.add(_route(method=None))
    other_path = store.add(_route(path="/api/other"))

    assert store.take("GET", "/api/orders") == FaultDecision(0, 500)
    assert store.take("POST", "/api/orders") == FaultDecision(0, 500)
    assert store.take("GET", "/api/other") == FaultDecision(0, 500)
    assert store.take("GET", "/api/orders/") is None
    assert store.list() == [first, any_method, other_path]


def test_times_counts_down_to_exhaustion() -> None:
    store = InMemoryFaultStore()
    store.add(_route(remaining=2))

    assert store.take("GET", "/api/orders") is not None
    assert store.take("GET", "/api/orders") is not None
    assert store.take("GET", "/api/orders") is None
    assert store.list() == []


def test_adding_a_rule_purges_the_exhausted_ones() -> None:
    store = InMemoryFaultStore()
    store.add(_route(remaining=1))
    store.take("GET", "/api/orders")

    stored = store.add(_route(path="/api/new"))

    assert stored.id == 2
    assert [rule.id for rule in store.list()] == [2]


def test_the_fifty_first_active_rule_is_rejected() -> None:
    store = InMemoryFaultStore()
    for index in range(MAX_FAULT_RULES):
        store.add(_route(path=f"/api/{index}"))

    with pytest.raises(TooManyFaultRules):
        store.add(_route(path="/api/too-many"))

    store.clear()
    assert store.list() == []
    assert store.add(_route(path="/api/again")).id == MAX_FAULT_RULES + 1


def test_take_gateway_only_matches_gateway_rules_and_consumes_them() -> None:
    store = InMemoryFaultStore()
    store.add(_route())
    store.add(NewRule(target="gateway", latency_ms=250, remaining=1))

    assert store.take_gateway() == FaultDecision(250, None)
    assert store.take_gateway() is None
    assert [rule.target for rule in store.list()] == ["route"]
