"""The email port: the invoice notice is written to the log only."""

from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class Mailer(Protocol):
    """An email port."""

    def invoice_issued(self, to_email: str, number: str) -> None: ...


class LoggingMailer:
    """A mailer that logs one line with the number and never the address."""

    def __init__(self, target: logging.Logger | None = None) -> None:
        self._logger = target if target is not None else logger

    def invoice_issued(self, to_email: str, number: str) -> None:
        """Log the notice. A logging failure is swallowed."""
        try:
            self._logger.info("Factura %s emitida", number)
        except Exception:
            pass
