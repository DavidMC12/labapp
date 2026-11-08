"""The seeded product catalog of docs/SEED.md."""

from __future__ import annotations

from app.modules.orders.seed import seed_products

from . import support


def test_the_fifteen_products_match_the_document() -> None:
    rows = support.seed_table(
        "Products",
        "Id",
        "SKU",
        "Name",
        "Price (USD)",
        "Stock",
        "Why it exists",
    )
    products = seed_products()

    assert len(rows) == len(products) == 15
    for row, product in zip(rows, products, strict=True):
        assert int(row["Id"]) == product.id
        assert row["SKU"] == product.sku
        assert row["Name"] == product.name
        assert row["Price (USD)"] == f"{product.price:.2f}"
        assert int(row["Stock"]) == product.stock
