"""Seeded products and orders."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.domain.orders import OrderStatus
from app.modules.orders.models import Order, OrderLine, Product

SEED_TAX_RATE = Decimal("10.00")

_PRODUCTS = [
    (1, "KB-100", "Teclado USB", "19.90", 120),
    (2, "MS-200", "Mouse óptico", "9.50", 195),
    (3, "MN-240", 'Monitor 24"', "149.00", 33),
    (4, "LP-300", 'Laptop 14"', "699.00", 11),
    (5, "HD-500", "Disco externo 1 TB", "59.99", 57),
    (6, "CB-010", "Cable HDMI 2 m", "6.25", 489),
    (7, "WC-720", "Cámara web HD", "34.50", 3),
    (8, "HS-110", "Audífonos con micrófono", "22.00", 78),
    (9, "PR-400", "Impresora láser", "189.90", 0),
    (10, "UP-650", "UPS 650 VA", "79.00", 18),
    (11, "RT-AC1", "Router doble banda", "44.75", 40),
    (12, "SW-8P", "Switch 8 puertos", "27.40", 25),
    (13, "DK-USB", "Hub USB-C 7 en 1", "31.20", 70),
    (14, "SD-128", "Tarjeta SD 128 GB", "14.99", 300),
    (15, "CH-ERG", "Silla ergonómica", "215.00", 8),
]


def seed_products() -> list[Product]:
    """Return the fifteen documented products with their post-seed stock."""
    return [
        Product(id=identifier, sku=sku, name=name, price=Decimal(price), stock=stock)
        for identifier, sku, name, price, stock in _PRODUCTS
    ]


def _line(
    identifier: int,
    product: Product,
    quantity: int,
) -> OrderLine:
    return OrderLine(
        id=identifier,
        product_id=product.id,
        sku=product.sku,
        name=product.name,
        quantity=quantity,
        unit_price=product.price,
    )


def seed_orders() -> list[Order]:
    """Return the seven documented orders and their lines."""
    products = {product.id: product for product in seed_products()}
    orders: list[Order] = [
        Order(
            id=1,
            number="PED-0001",
            status=OrderStatus.DRAFT,
            customer_id=1,
            lines=(_line(1, products[1], 2),),
            tax_rate=None,
            version=1,
            created_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
            invoice_id=None,
        ),
        Order(
            id=2,
            number="PED-0002",
            status=OrderStatus.CONFIRMED,
            customer_id=2,
            lines=(_line(2, products[2], 5), _line(3, products[6], 10)),
            tax_rate=SEED_TAX_RATE,
            version=1,
            created_at=datetime(2026, 1, 2, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 1, 2, 10, 0, tzinfo=UTC),
            invoice_id=None,
        ),
        Order(
            id=3,
            number="PED-0003",
            status=OrderStatus.CONFIRMED,
            customer_id=4,
            lines=(_line(4, products[3], 2),),
            tax_rate=SEED_TAX_RATE,
            version=1,
            created_at=datetime(2026, 1, 3, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 1, 3, 10, 0, tzinfo=UTC),
            invoice_id=None,
        ),
        Order(
            id=4,
            number="PED-0004",
            status=OrderStatus.PAID,
            customer_id=6,
            lines=(_line(5, products[5], 3),),
            tax_rate=SEED_TAX_RATE,
            version=1,
            created_at=datetime(2026, 1, 4, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 1, 4, 10, 0, tzinfo=UTC),
            invoice_id=None,
        ),
        Order(
            id=5,
            number="PED-0005",
            status=OrderStatus.SHIPPED,
            customer_id=9,
            lines=(_line(6, products[4], 1),),
            tax_rate=SEED_TAX_RATE,
            version=1,
            created_at=datetime(2026, 1, 5, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 1, 5, 10, 0, tzinfo=UTC),
            invoice_id=None,
        ),
        Order(
            id=6,
            number="PED-0006",
            status=OrderStatus.CANCELLED,
            customer_id=10,
            lines=(_line(7, products[12], 4),),
            tax_rate=SEED_TAX_RATE,
            version=1,
            created_at=datetime(2026, 1, 6, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 1, 6, 10, 0, tzinfo=UTC),
            invoice_id=None,
        ),
        Order(
            id=7,
            number="PED-0007",
            status=OrderStatus.CONFIRMED,
            customer_id=3,
            lines=(_line(8, products[8], 2), _line(9, products[6], 1)),
            tax_rate=SEED_TAX_RATE,
            version=1,
            created_at=datetime(2026, 1, 7, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 1, 7, 10, 0, tzinfo=UTC),
            invoice_id=None,
        ),
    ]
    return orders
