"""Spanish labels for domain values."""

from __future__ import annotations

ORDER_STATUS_LABELS: dict[str, str] = {
    "draft": "borrador",
    "confirmed": "confirmado",
    "paid": "pagado",
    "shipped": "enviado",
    "cancelled": "cancelado",
}

INVOICE_STATUS_LABELS: dict[str, str] = {
    "issued": "emitida",
    "paid": "pagada",
    "void": "anulada",
}

PAYMENT_STATUS_LABELS: dict[str, str] = {
    "approved": "aprobado",
    "declined": "rechazado",
    "failed": "fallido",
}

PAYMENT_METHOD_LABELS: dict[str, str] = {
    "card": "tarjeta",
    "transfer": "transferencia",
    "cash": "efectivo",
}

ROLE_LABELS: dict[str, str] = {
    "admin": "Admin",
    "sales": "Ventas",
    "finance": "Finanzas",
    "readonly": "Solo lectura",
}
