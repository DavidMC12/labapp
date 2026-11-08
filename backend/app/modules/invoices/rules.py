"""The invoice and payment business errors in one place."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from typing import Protocol

from app.domain.money import LineInput, Totals, compute_totals, quantize_money
from app.domain.orders import OrderStatus
from app.errors import ApiError
from app.modules.invoices.models import InvoiceStatus

INVOICE_ALREADY_EXISTS_MESSAGE = "Este pedido ya tiene una factura."
ORDER_NOT_INVOICEABLE_MESSAGE = "Solo se puede facturar un pedido confirmado."
CUSTOMER_TAX_ID_REQUIRED_MESSAGE = "El cliente necesita un ID fiscal para poder facturar."
INVOICE_NOT_PAYABLE_MESSAGE = "Esta factura no admite pagos."
PAYMENT_AMOUNT_MISMATCH_MESSAGE = "El monto debe ser igual al total de la factura."
PAYMENT_DECLINED_MESSAGE = "La pasarela rechazó el pago. Prueba con otra tarjeta."
PAYMENT_GATEWAY_UNAVAILABLE_MESSAGE = "La pasarela de pago no está disponible. Inténtalo de nuevo."
IDEMPOTENCY_KEY_REUSED_MESSAGE = "Esa clave de idempotencia ya se usó con otros datos."


def invoice_already_exists() -> ApiError:
    """Return the error for a second invoice of one order."""
    return ApiError(409, "INVOICE_ALREADY_EXISTS", INVOICE_ALREADY_EXISTS_MESSAGE)


def order_not_invoiceable() -> ApiError:
    """Return the error for an order that is not confirmed."""
    return ApiError(409, "ORDER_NOT_INVOICEABLE", ORDER_NOT_INVOICEABLE_MESSAGE)


def customer_tax_id_required() -> ApiError:
    """Return the error for a customer without a tax id."""
    return ApiError(422, "CUSTOMER_TAX_ID_REQUIRED", CUSTOMER_TAX_ID_REQUIRED_MESSAGE)


def invoice_not_payable() -> ApiError:
    """Return the error for an invoice that is not issued."""
    return ApiError(409, "INVOICE_NOT_PAYABLE", INVOICE_NOT_PAYABLE_MESSAGE)


def amount_mismatch() -> ApiError:
    """Return the error for a payment that is not the full total."""
    return ApiError(422, "PAYMENT_AMOUNT_MISMATCH", PAYMENT_AMOUNT_MISMATCH_MESSAGE)


def key_reused() -> ApiError:
    """Return the error for an idempotency key used with another body."""
    return ApiError(422, "IDEMPOTENCY_KEY_REUSED", IDEMPOTENCY_KEY_REUSED_MESSAGE)


def payment_declined(payment_id: int, reason: str | None) -> ApiError:
    """Return the problem for a declined payment."""
    return ApiError(
        402,
        "PAYMENT_DECLINED",
        PAYMENT_DECLINED_MESSAGE,
        payment_id=payment_id,
        reason=reason,
    )


def gateway_unavailable(payment_id: int, reason: str | None) -> ApiError:
    """Return the problem for an unavailable gateway."""
    return ApiError(
        503,
        "PAYMENT_GATEWAY_UNAVAILABLE",
        PAYMENT_GATEWAY_UNAVAILABLE_MESSAGE,
        payment_id=payment_id,
        reason=reason,
    )


def ensure_can_invoice(
    order_status: OrderStatus,
    has_invoice: bool,
    tax_id: str | None,
) -> None:
    """Raise the first rule that blocks issuing the invoice."""
    if has_invoice:
        raise invoice_already_exists()
    if order_status != OrderStatus.CONFIRMED:
        raise order_not_invoiceable()
    if not tax_id:
        raise customer_tax_id_required()


def ensure_payable(status: InvoiceStatus) -> None:
    """Raise unless the invoice is issued."""
    if status != InvoiceStatus.ISSUED:
        raise invoice_not_payable()


def ensure_amount(amount: Decimal, total: Decimal) -> None:
    """Raise unless the payment is the full total, compared with two decimals."""
    if quantize_money(amount) != quantize_money(total):
        raise amount_mismatch()


class PricedLine(Protocol):
    """A line that can be priced into totals."""

    unit_price: Decimal
    quantity: int


def totals_for(lines: Iterable[PricedLine], rate: Decimal) -> Totals:
    """Compute the totals of invoice-like lines with a tax rate."""
    return compute_totals(
        [LineInput(line.unit_price, line.quantity) for line in lines],
        rate,
    )
