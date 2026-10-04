"""Inventory tool handler.

WooCommerce does not have a separate inventory endpoint.  Stock data is part
of the product resource, so this handler queries ``/products`` and returns
only inventory-relevant fields.
"""

from __future__ import annotations

from app.client.woo_client import WooCommerceClient
from app.models.common import PaginatedResponse
from app.models.inventory import InventoryItem, normalize_inventory


def _clamp_per_page(per_page: int) -> int:
    return max(1, min(per_page, 100))


async def handle_check_inventory(
    client: WooCommerceClient,
    *,
    product_id: int | None = None,
    stock_status: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> InventoryItem | PaginatedResponse[InventoryItem]:
    """Check inventory for one product or list products filtered by stock status.

    When ``product_id`` is provided, returns a single ``InventoryItem``.
    Otherwise returns a paginated list (optionally filtered by ``stock_status``).
    """
    if product_id is not None:
        resp = await client.get(f"products/{product_id}")
        return normalize_inventory(resp.data)  # type: ignore[arg-type]

    params: dict = {"page": max(page, 1), "per_page": _clamp_per_page(per_page)}
    if stock_status:
        params["stock_status"] = stock_status

    resp = await client.get("products", params=params)
    items = [normalize_inventory(p) for p in resp.data]  # type: ignore[union-attr]
    return PaginatedResponse(
        data=items,
        page=params["page"],
        per_page=params["per_page"],
        total=resp.total,
        total_pages=resp.total_pages,
    )
