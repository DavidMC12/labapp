"""The seeded customers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.modules.customers.models import Customer, CustomerStatus

SEED_CREATED_AT = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)

_CUSTOMERS = [
    (
        "Acme Industrial S.A.",
        "acme@example.test",
        "+1 555 010 0001",
        "ACME-900123",
        "Av. Principal 100",
        CustomerStatus.ACTIVE,
    ),
    ("Beta Comercial Ltda.", "beta@example.test", None, "BETA-800456", None, CustomerStatus.ACTIVE),
    ("Cafetería La Esquina", "cafe@example.test", None, None, None, CustomerStatus.ACTIVE),
    ("Distribuidora Delta", "delta@example.test", None, "DELT-700789", None, CustomerStatus.ACTIVE),
    ("Estudio Épsilon", "epsilon@example.test", None, "EPSI-600321", None, CustomerStatus.INACTIVE),
    ("Ferretería Fénix", "fenix@example.test", None, "FENI-500654", None, CustomerStatus.ACTIVE),
    (
        "Grupo Gamma Servicios Profesionales y Consultoría Internacional de "
        "Latinoamérica Sociedad por Acciones Simplificada",
        "gamma@example.test",
        None,
        "GAMM-400111",
        None,
        CustomerStatus.ACTIVE,
    ),
    ("Hotel Horizonte", "hotel@example.test", None, None, None, CustomerStatus.INACTIVE),
    (
        "Ibérica Importaciones",
        "iberica@example.test",
        None,
        "IBER-400987",
        None,
        CustomerStatus.ACTIVE,
    ),
    ("Joyería Júpiter", "joyeria@example.test", None, "JUPI-300210", None, CustomerStatus.ACTIVE),
]


def seed_customers() -> list[Customer]:
    """Return the ten documented customers."""
    customers: list[Customer] = []
    for identifier, (name, email, phone, tax_id, address, status) in enumerate(_CUSTOMERS, start=1):
        created_at = SEED_CREATED_AT + timedelta(minutes=identifier)
        customers.append(
            Customer(
                id=identifier,
                name=name,
                email=email,
                phone=phone,
                tax_id=tax_id,
                address=address,
                status=status,
                version=1,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    return customers
