"""The replaceable payment gateway."""

from __future__ import annotations

import time
from collections.abc import Callable
from decimal import Decimal
from typing import Protocol

from app.domain.payments import GatewayDecision, gateway_decision
from app.modules.testcontrols.ports import FaultStore


class PaymentGateway(Protocol):
    """A payment gateway that decides the outcome of one charge."""

    def charge(
        self,
        method: str,
        amount: Decimal,
        card_last4: str | None,
    ) -> GatewayDecision: ...


class FakeGateway:
    """The documented fake gateway, built on the pure domain decision."""

    def charge(
        self,
        method: str,
        amount: Decimal,
        card_last4: str | None,
    ) -> GatewayDecision:
        """Return the decision for a payment method and the card's last four digits."""
        return gateway_decision(method, card_last4)


class FaultyGateway:
    """A gateway that consumes test faults before asking the inner gateway.

    ``enabled`` is false in production, so the store is never queried and a stale
    rule cannot affect payments.
    """

    def __init__(
        self,
        inner: PaymentGateway,
        store: FaultStore,
        sleep: Callable[[float], None] = time.sleep,
        *,
        enabled: bool = True,
    ) -> None:
        self._inner = inner
        self._store = store
        self._sleep = sleep
        self._enabled = enabled

    def charge(
        self,
        method: str,
        amount: Decimal,
        card_last4: str | None,
    ) -> GatewayDecision:
        """Inject an unavailable answer when a gateway rule is consumed."""
        if not self._enabled:
            return self._inner.charge(method, amount, card_last4)

        decision = self._store.take_gateway()
        if decision is None:
            return self._inner.charge(method, amount, card_last4)

        self._sleep(min(decision.latency_ms, 10_000) / 1000)
        return GatewayDecision("unavailable", "GATEWAY_UNAVAILABLE")
