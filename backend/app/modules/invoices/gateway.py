"""The replaceable payment gateway."""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from app.domain.payments import GatewayDecision, gateway_decision


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
