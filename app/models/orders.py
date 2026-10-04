"""Agent-facing order models.

Normalization decisions
-----------------------
* ``customer`` is flattened to id + email (from ``billing.email``).
* ``items`` are extracted from ``line_items`` with only agent-useful fields.
* Internal WooCommerce metadata (``meta_data``, ``_links``, tax details) is dropped.
"""

from __future__ import annotations

from pydantic import BaseModel


class OrderItem(BaseModel):
    product_id: int
    name: str
    quantity: int
    subtotal: str
    sku: str | None = None


class OrderCustomer(BaseModel):
    id: int
    email: str | None = None


class Order(BaseModel):
    id: int
    status: str
    currency: str
    total: str
    customer: OrderCustomer
    created_at: str
    updated_at: str
    items: list[OrderItem]
    payment_method: str | None = None
    note: str | None = None


def normalize_order(raw: dict) -> Order:
    """Convert raw WooCommerce order JSON to an ``Order``."""
    return Order(
        id=raw["id"],
        status=raw["status"],
        currency=raw["currency"],
        total=raw["total"],
        customer=OrderCustomer(
            id=raw.get("customer_id", 0),
            email=raw.get("billing", {}).get("email"),
        ),
        created_at=raw["date_created"],
        updated_at=raw["date_modified"],
        items=[
            OrderItem(
                product_id=li["product_id"],
                name=li["name"],
                quantity=li["quantity"],
                subtotal=li["subtotal"],
                sku=li.get("sku"),
            )
            for li in raw.get("line_items", [])
        ],
        payment_method=raw.get("payment_method") or None,
        note=raw.get("customer_note") or None,
    )
