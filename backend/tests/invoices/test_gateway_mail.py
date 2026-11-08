"""Tests for the fake gateway and the logging mailer."""

from __future__ import annotations

import logging
from decimal import Decimal

import pytest

from app.domain.payments import GatewayDecision
from app.modules.invoices.gateway import FakeGateway
from app.modules.invoices.mail import LoggingMailer


@pytest.mark.parametrize(
    ("method", "last4", "expected"),
    [
        ("card", "4242", GatewayDecision("approved", None)),
        ("card", "0002", GatewayDecision("declined", "CARD_DECLINED")),
        ("card", "0003", GatewayDecision("unavailable", "GATEWAY_UNAVAILABLE")),
        ("transfer", None, GatewayDecision("approved", None)),
        ("cash", None, GatewayDecision("approved", None)),
    ],
)
def test_the_fake_gateway_uses_the_domain_decisions(
    method: str,
    last4: str | None,
    expected: GatewayDecision,
) -> None:
    assert FakeGateway().charge(method, Decimal("10.00"), last4) == expected


def test_the_logging_mailer_logs_the_number_and_never_the_address(
    caplog: pytest.LogCaptureFixture,
) -> None:
    mailer = LoggingMailer()

    with caplog.at_level(logging.INFO):
        mailer.invoice_issued("customer@example.test", "FAC-0004")

    assert [record.getMessage() for record in caplog.records] == ["Factura FAC-0004 emitida"]
    assert "customer@example.test" not in caplog.text


class _BrokenLogger:
    def info(self, *args: object, **kwargs: object) -> None:
        raise RuntimeError("logging failed")


def test_the_logging_mailer_never_raises() -> None:
    LoggingMailer(_BrokenLogger()).invoice_issued("customer@example.test", "FAC-0004")
