"""The named examples of the OpenAPI contract.

Every example lives here once: the routes publish these values in the contract and the
tests import the same values, so a documented body and the body a test sends cannot drift
apart. The values follow ``docs/SPEC.md`` and ``docs/SEED.md``: ids, names, numbers and
amounts are the ones the demo data has after a reset.
"""

from __future__ import annotations

from typing import Any

from app.modules.auth.seed import DEMO_PASSWORD

Example = dict[str, Any]
NamedExamples = dict[str, Example]


def named(summary: str, value: Example) -> Example:
    """Return one named example in the shape OpenAPI expects."""
    return {"summary": summary, "value": value}


# Requests -------------------------------------------------------------------------

LOGIN_REQUEST: Example = {"email": "admin@labapp.test", "password": DEMO_PASSWORD}
LOGIN_EXAMPLES: NamedExamples = {
    "admin": named("The admin demo user printed on the login screen", LOGIN_REQUEST)
}

CUSTOMER_CREATE_MINIMAL_REQUEST: Example = {
    "name": "Aurora Servicios S.A.",
    "email": "aurora@example.test",
}
CUSTOMER_CREATE_FULL_REQUEST: Example = {
    "name": "Northwind Import S.A.",
    "email": "northwind@example.test",
    "phone": "+1 555 010 0200",
    "tax_id": "NORTH-123456",
    "address": "Calle 50, edificio 12\nPiso 3",
}
CUSTOMER_CREATE_EXAMPLES: NamedExamples = {
    "minimal": named(
        "Only the two required fields",
        CUSTOMER_CREATE_MINIMAL_REQUEST,
    ),
    "full": named(
        "Every field, including a multi-line address",
        CUSTOMER_CREATE_FULL_REQUEST,
    ),
}

CUSTOMER_PATCH_REQUEST: Example = {
    "phone": "+1 555 010 0099",
    "address": "Av. Principal 100, piso 2",
    "version": 1,
}
CUSTOMER_PATCH_EXAMPLES: NamedExamples = {
    "update-contact": named(
        "Change the phone and the address of customer 1",
        CUSTOMER_PATCH_REQUEST,
    )
}

ORDER_CREATE_REQUEST: Example = {"customer_id": 1}
ORDER_CREATE_EXAMPLES: NamedExamples = {
    "new-draft": named("Start a draft for Acme Industrial S.A.", ORDER_CREATE_REQUEST)
}

ORDER_CUSTOMER_PATCH_REQUEST: Example = {"customer_id": 2, "version": 1}
ORDER_CUSTOMER_PATCH_EXAMPLES: NamedExamples = {
    "change-customer": named(
        "Move the draft to Beta Comercial Ltda.",
        ORDER_CUSTOMER_PATCH_REQUEST,
    )
}

ORDER_LINE_CREATE_REQUEST: Example = {"product_id": 1, "quantity": 2, "version": 1}
ORDER_LINE_CREATE_EXAMPLES: NamedExamples = {
    "add-keyboard": named(
        "Add two keyboards to the draft",
        ORDER_LINE_CREATE_REQUEST,
    )
}

ORDER_LINE_PATCH_REQUEST: Example = {"quantity": 3, "version": 1}
ORDER_LINE_PATCH_EXAMPLES: NamedExamples = {
    "change-quantity": named(
        "Raise the quantity of the first line of PED-0001",
        ORDER_LINE_PATCH_REQUEST,
    )
}

SETTINGS_PATCH_REQUEST: Example = {"tax_rate": "12.50"}
SETTINGS_PATCH_EXAMPLES: NamedExamples = {
    "set-tax-rate": named("Set the tax rate to 12.50%", SETTINGS_PATCH_REQUEST)
}

CARD_APPROVED_REQUEST: Example = {
    "method": "card",
    "amount": "121.00",
    "card": {"number": "4242 4242 4242 4242", "expiry": "12/30", "cvc": "123"},
}
CARD_DECLINED_REQUEST: Example = {
    "method": "card",
    "amount": "327.80",
    "card": {"number": "4000 0000 0000 0002", "expiry": "12/30", "cvc": "123"},
}
TRANSFER_REQUEST: Example = {
    "method": "transfer",
    "amount": "327.80",
    "reference": "TRF-2026-0002",
}
CASH_REQUEST: Example = {"method": "cash", "amount": "327.80"}
PAYMENT_EXAMPLES: NamedExamples = {
    "card-approved": named(
        "A card the fake gateway approves",
        CARD_APPROVED_REQUEST,
    ),
    "card-declined": named(
        "The test card whose last four digits are 0002",
        CARD_DECLINED_REQUEST,
    ),
    "transfer": named("A transfer with a reference", TRANSFER_REQUEST),
    "cash": named("A cash payment, with no extra data", CASH_REQUEST),
}


# Answers --------------------------------------------------------------------------

CUSTOMER_CREATED_201: Example = {
    "id": 11,
    "name": "Northwind Import S.A.",
    "email": "northwind@example.test",
    "phone": "+1 555 010 0200",
    "tax_id": "NORTH-123456",
    "address": "Calle 50, edificio 12\nPiso 3",
    "status": "active",
    "version": 1,
    "created_at": "2026-11-05T15:00:00Z",
    "updated_at": "2026-11-05T15:00:00Z",
}
CUSTOMER_CREATED_EXAMPLES: NamedExamples = {
    "created": named("The new customer", CUSTOMER_CREATED_201)
}

ORDER_CREATED_201: Example = {
    "id": 8,
    "number": "PED-0008",
    "status": "draft",
    "customer": {"id": 1, "name": "Acme Industrial S.A.", "status": "active"},
    "lines": [],
    "subtotal": "0.00",
    "tax_rate": "10.00",
    "tax": "0.00",
    "total": "0.00",
    "invoice_id": None,
    "version": 1,
    "created_at": "2026-11-05T15:00:00Z",
    "updated_at": "2026-11-05T15:00:00Z",
}
ORDER_CREATED_EXAMPLES: NamedExamples = {"created": named("The new empty draft", ORDER_CREATED_201)}

ORDER_LINE_CREATED_201: Example = {
    "id": 8,
    "number": "PED-0008",
    "status": "draft",
    "customer": {"id": 1, "name": "Acme Industrial S.A.", "status": "active"},
    "lines": [
        {
            "id": 10,
            "product_id": 1,
            "sku": "KB-100",
            "name": "Teclado USB",
            "quantity": 2,
            "unit_price": "19.90",
            "line_total": "39.80",
        }
    ],
    "subtotal": "39.80",
    "tax_rate": "10.00",
    "tax": "3.98",
    "total": "43.78",
    "invoice_id": None,
    "version": 2,
    "created_at": "2026-11-05T15:00:00Z",
    "updated_at": "2026-11-05T15:01:00Z",
}
ORDER_LINE_CREATED_EXAMPLES: NamedExamples = {
    "line-added": named("The draft with its first line", ORDER_LINE_CREATED_201)
}

INVOICE_ISSUED_201: Example = {
    "id": 4,
    "number": "FAC-0004",
    "status": "issued",
    "order_id": 2,
    "order_number": "PED-0002",
    "customer": {
        "id": 2,
        "name": "Beta Comercial Ltda.",
        "tax_id": "BETA-800456",
        "address": None,
    },
    "lines": [
        {
            "id": 4,
            "product_id": 2,
            "sku": "MS-200",
            "name": "Mouse óptico",
            "quantity": 5,
            "unit_price": "9.50",
            "line_total": "47.50",
        },
        {
            "id": 5,
            "product_id": 6,
            "sku": "CB-010",
            "name": "Cable HDMI 2 m",
            "quantity": 10,
            "unit_price": "6.25",
            "line_total": "62.50",
        },
    ],
    "subtotal": "110.00",
    "tax_rate": "10.00",
    "tax": "11.00",
    "total": "121.00",
    "payments": [],
    "version": 1,
    "created_at": "2026-11-05T15:00:00Z",
    "updated_at": "2026-11-05T15:00:00Z",
}
INVOICE_ISSUED_EXAMPLES: NamedExamples = {
    "issued": named("The invoice of PED-0002", INVOICE_ISSUED_201)
}

PAYMENT_APPROVED_201: Example = {
    "payment": {
        "id": 5,
        "method": "card",
        "status": "approved",
        "amount": "121.00",
        "reference": None,
        "card_last4": "4242",
        "reason": None,
        "created_at": "2026-11-05T15:02:00Z",
    },
    "invoice": {
        "id": 4,
        "number": "FAC-0004",
        "status": "paid",
        "order_id": 2,
        "order_number": "PED-0002",
        "customer": {
            "id": 2,
            "name": "Beta Comercial Ltda.",
            "tax_id": "BETA-800456",
            "address": None,
        },
        "lines": [
            {
                "id": 4,
                "product_id": 2,
                "sku": "MS-200",
                "name": "Mouse óptico",
                "quantity": 5,
                "unit_price": "9.50",
                "line_total": "47.50",
            },
            {
                "id": 5,
                "product_id": 6,
                "sku": "CB-010",
                "name": "Cable HDMI 2 m",
                "quantity": 10,
                "unit_price": "6.25",
                "line_total": "62.50",
            },
        ],
        "subtotal": "110.00",
        "tax_rate": "10.00",
        "tax": "11.00",
        "total": "121.00",
        "payments": [
            {
                "id": 5,
                "method": "card",
                "status": "approved",
                "amount": "121.00",
                "reference": None,
                "card_last4": "4242",
                "reason": None,
                "created_at": "2026-11-05T15:02:00Z",
            }
        ],
        "version": 2,
        "created_at": "2026-11-05T15:00:00Z",
        "updated_at": "2026-11-05T15:02:00Z",
    },
}
PAYMENT_APPROVED_EXAMPLES: NamedExamples = {
    "approved": named("The approved card payment and the paid invoice", PAYMENT_APPROVED_201)
}

PAYMENT_DECLINED_402: Example = {
    "type": "about:blank",
    "title": "Payment Required",
    "status": 402,
    "code": "PAYMENT_DECLINED",
    "detail": "La pasarela rechazó el pago. Prueba con otra tarjeta.",
    "payment_id": 5,
    "reason": "CARD_DECLINED",
}
PAYMENT_DECLINED_EXAMPLES: NamedExamples = {
    "declined": named("The stored declined attempt", PAYMENT_DECLINED_402)
}

UNAUTHENTICATED_401: Example = {
    "type": "about:blank",
    "title": "Unauthorized",
    "status": 401,
    "code": "UNAUTHENTICATED",
    "detail": "Inicia sesión para continuar.",
}
INVALID_CREDENTIALS_401: Example = {
    "type": "about:blank",
    "title": "Unauthorized",
    "status": 401,
    "code": "INVALID_CREDENTIALS",
    "detail": "Email o contraseña incorrectos.",
}
FORBIDDEN_403: Example = {
    "type": "about:blank",
    "title": "Forbidden",
    "status": 403,
    "code": "FORBIDDEN",
    "detail": "No tienes permiso para realizar esta acción.",
}
NOT_FOUND_404: Example = {
    "type": "about:blank",
    "title": "Not Found",
    "status": 404,
    "code": "NOT_FOUND",
    "detail": "No se encontró el recurso solicitado.",
}
VERSION_CONFLICT_409: Example = {
    "type": "about:blank",
    "title": "Conflict",
    "status": 409,
    "code": "VERSION_CONFLICT",
    "detail": "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo.",
}
CUSTOMER_EMAIL_TAKEN_409: Example = {
    "type": "about:blank",
    "title": "Conflict",
    "status": 409,
    "code": "CUSTOMER_EMAIL_TAKEN",
    "detail": "Ya existe un cliente con ese email.",
}
CSRF_ORIGIN_MISMATCH_403: Example = {
    "type": "about:blank",
    "title": "Forbidden",
    "status": 403,
    "code": "CSRF_ORIGIN_MISMATCH",
    "detail": "La solicitud no proviene de la aplicación.",
}
VALIDATION_ERROR_422: Example = {
    "type": "about:blank",
    "title": "Unprocessable Content",
    "status": 422,
    "code": "VALIDATION_ERROR",
    "detail": "Revisa los datos ingresados.",
    "errors": [
        {
            "field": "quantity",
            "code": "OUT_OF_RANGE",
            "message": "El valor debe estar entre 1 y 999.",
        }
    ],
}

# One named example per common problem: every answer with that status publishes this one.
PROBLEM_EXAMPLES: dict[int, NamedExamples] = {
    401: {"unauthenticated": named("No session", UNAUTHENTICATED_401)},
    402: PAYMENT_DECLINED_EXAMPLES,
    403: {"forbidden": named("The role lacks the permission", FORBIDDEN_403)},
    404: {"not-found": named("The resource does not exist", NOT_FOUND_404)},
    409: {"version-conflict": named("A stale version", VERSION_CONFLICT_409)},
    422: {"validation-error": named("One invalid field", VALIDATION_ERROR_422)},
}
INVALID_CREDENTIALS_EXAMPLES: NamedExamples = {
    "invalid-credentials": named("A wrong email or password", INVALID_CREDENTIALS_401)
}
CUSTOMER_EMAIL_TAKEN_EXAMPLES: NamedExamples = {
    "email-taken": named("The email already belongs to another customer", CUSTOMER_EMAIL_TAKEN_409)
}
CSRF_ORIGIN_MISMATCH_EXAMPLES: NamedExamples = {
    "origin-mismatch": named(
        "The Origin is not the application origin",
        CSRF_ORIGIN_MISMATCH_403,
    )
}


# The contract -----------------------------------------------------------------------
# FastAPI drops `None` members while it serializes the document, and several documented
# answers carry nulls (`invoice_id`, `address`, `reference`, `reason`). `install_openapi`
# replays these values after generation so the contract keeps the nulls the SPEC shows.

OPERATION_EXAMPLES: dict[tuple[str, str], dict[str, Any]] = {
    ("POST", "/api/auth/login"): {"request": LOGIN_EXAMPLES},
    ("POST", "/api/customers"): {
        "request": CUSTOMER_CREATE_EXAMPLES,
        "responses": {"201": CUSTOMER_CREATED_EXAMPLES},
    },
    ("PATCH", "/api/customers/{id}"): {"request": CUSTOMER_PATCH_EXAMPLES},
    ("POST", "/api/orders"): {
        "request": ORDER_CREATE_EXAMPLES,
        "responses": {"201": ORDER_CREATED_EXAMPLES},
    },
    ("PATCH", "/api/orders/{id}"): {"request": ORDER_CUSTOMER_PATCH_EXAMPLES},
    ("POST", "/api/orders/{id}/lines"): {
        "request": ORDER_LINE_CREATE_EXAMPLES,
        "responses": {"201": ORDER_LINE_CREATED_EXAMPLES},
    },
    ("PATCH", "/api/orders/{id}/lines/{line_id}"): {"request": ORDER_LINE_PATCH_EXAMPLES},
    ("PATCH", "/api/settings"): {"request": SETTINGS_PATCH_EXAMPLES},
    ("POST", "/api/orders/{id}/invoice"): {"responses": {"201": INVOICE_ISSUED_EXAMPLES}},
    ("POST", "/api/invoices/{id}/payments"): {
        "request": PAYMENT_EXAMPLES,
        "responses": {
            "201": PAYMENT_APPROVED_EXAMPLES,
            "402": PAYMENT_DECLINED_EXAMPLES,
        },
    },
}
