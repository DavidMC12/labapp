"""The faulty gateway inside a real payment."""

from __future__ import annotations

from decimal import Decimal

from app.domain.payments import GatewayDecision
from app.modules.invoices.gateway import FaultyGateway
from app.modules.testcontrols.memory import InMemoryFaultStore
from app.modules.testcontrols.models import FaultDecision, NewRule


class RecordingGateway:
    """An inner gateway that records whether it was called."""

    def __init__(self) -> None:
        self.calls = 0

    def charge(self, method: str, amount: Decimal, card_last4: str | None):
        self.calls += 1
        return GatewayDecision("approved", None)


class FixedFaultStore(InMemoryFaultStore):
    """A fault store that always returns the same gateway decision."""

    def __init__(self, decision: FaultDecision | None) -> None:
        super().__init__()
        self.decision = decision

    def take_gateway(self, **kwargs: object) -> FaultDecision | None:
        return self.decision


class Sleeper:
    def __init__(self) -> None:
        self.waits: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.waits.append(seconds)


def test_without_a_decision_it_calls_the_inner_gateway() -> None:
    inner = RecordingGateway()
    gateway = FaultyGateway(inner, InMemoryFaultStore(), sleep=Sleeper())

    decision = gateway.charge("card", Decimal("10.00"), "4242")

    assert decision.outcome == "approved"
    assert inner.calls == 1


def test_a_disabled_gateway_never_reads_the_store() -> None:
    inner = RecordingGateway()
    store = FixedFaultStore(FaultDecision(20_000, None))
    gateway = FaultyGateway(inner, store, sleep=Sleeper(), enabled=False)

    decision = gateway.charge("card", Decimal("10.00"), "4242")

    assert decision.outcome == "approved"
    assert inner.calls == 1


def test_a_gateway_rule_skips_the_inner_gateway_and_caps_the_latency() -> None:
    inner = RecordingGateway()
    sleeper = Sleeper()
    store = FixedFaultStore(FaultDecision(20_000, None))
    gateway = FaultyGateway(inner, store, sleep=sleeper)

    decision = gateway.charge("card", Decimal("10.00"), "4242")

    assert decision.outcome == "unavailable"
    assert decision.reason == "GATEWAY_UNAVAILABLE"
    assert inner.calls == 0
    assert sleeper.waits == [10.0]


def test_a_gateway_rule_is_consumed_once() -> None:
    inner = RecordingGateway()
    store = InMemoryFaultStore()
    store.add(NewRule(target="gateway", remaining=1))
    gateway = FaultyGateway(inner, store, sleep=Sleeper())

    assert gateway.charge("cash", Decimal("10.00"), None).outcome == "unavailable"
    assert gateway.charge("cash", Decimal("10.00"), None).outcome == "approved"
    assert inner.calls == 1
