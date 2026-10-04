"""Agent-facing product models.

Normalization decisions
-----------------------
* ``categories`` are flattened to a list of names (WooCommerce sends nested objects).
* Prices are kept as strings to avoid floating-point issues.
* Internal metadata, cross-sell/upsell IDs, and rendering fields are dropped.
"""

from __future__ import annotations

from pydantic import BaseModel


class Product(BaseModel):
    id: int
    name: str
    slug: str
    status: str
    sku: str | None = None
    price: str
    regular_price: str
    sale_price: str | None = None
    stock_quantity: int | None = None
    stock_status: str
    categories: list[str]
    created_at: str


def normalize_product(raw: dict) -> Product:
    """Convert raw WooCommerce product JSON to a ``Product``."""
    return Product(
        id=raw["id"],
        name=raw["name"],
        slug=raw["slug"],
        status=raw["status"],
        sku=raw.get("sku") or None,
        price=raw.get("price", ""),
        regular_price=raw.get("regular_price", ""),
        sale_price=raw.get("sale_price") or None,
        stock_quantity=raw.get("stock_quantity"),
        stock_status=raw.get("stock_status", "instock"),
        categories=[
            c["name"] for c in raw.get("categories", []) if "name" in c
        ],
        created_at=raw["date_created"],
    )
