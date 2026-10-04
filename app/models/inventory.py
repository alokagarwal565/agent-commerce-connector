"""Agent-facing inventory model.

WooCommerce does not expose a separate inventory endpoint.  Inventory data
lives on the product resource, so this model is populated from the same
``/products`` response but only surfaces stock-relevant fields.
"""

from __future__ import annotations

from pydantic import BaseModel


class InventoryItem(BaseModel):
    product_id: int
    name: str
    sku: str | None = None
    stock_quantity: int | None = None
    stock_status: str  # instock | outofstock | onbackorder
    manage_stock: bool
    low_stock_threshold: int | None = None


def normalize_inventory(raw: dict) -> InventoryItem:
    """Extract inventory-relevant fields from a WooCommerce product."""
    return InventoryItem(
        product_id=raw["id"],
        name=raw["name"],
        sku=raw.get("sku") or None,
        stock_quantity=raw.get("stock_quantity"),
        stock_status=raw.get("stock_status", "instock"),
        manage_stock=bool(raw.get("manage_stock", False)),
        low_stock_threshold=raw.get("low_stock_amount"),
    )
