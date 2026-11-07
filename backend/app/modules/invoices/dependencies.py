"""FastAPI dependencies for the invoices module."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.modules.invoices.models import Invoice
from app.modules.invoices.service import InvoiceService


def get_service(request: Request) -> InvoiceService:
    """Return the invoice service built by create_app."""
    return request.app.state.invoices


def get_invoice(
    id: int,
    service: Annotated[InvoiceService, Depends(get_service)],
) -> Invoice:
    """Load the invoice or raise the 404 problem before the body is validated."""
    return service.get(id)
