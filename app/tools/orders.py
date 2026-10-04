"""Order tool handlers – validation, WooCommerce call, normalization."""

from __future__ import annotations

from app.client.woo_client import WooCommerceClient
from app.models.common import PaginatedResponse
from app.models.orders import Order, normalize_order


def _clamp_per_page(per_page: int) -> int:
    return max(1, min(per_page, 100))


async def handle_list_orders(
    client: WooCommerceClient,
    *,
    page: int = 1,
    per_page: int = 20,
    status: str | None = None,
    customer: int | None = None,
    after: str | None = None,
    before: str | None = None,
) -> PaginatedResponse[Order]:
    params: dict = {"page": max(page, 1), "per_page": _clamp_per_page(per_page)}
    if status:
        params["status"] = status
    if customer is not None:
        params["customer"] = customer
    if after:
        params["after"] = after
    if before:
        params["before"] = before

    resp = await client.get("orders", params=params)
    orders = [normalize_order(o) for o in resp.data]  # type: ignore[union-attr]
    return PaginatedResponse(
        data=orders,
        page=params["page"],
        per_page=params["per_page"],
        total=resp.total,
        total_pages=resp.total_pages,
    )


async def handle_get_order(
    client: WooCommerceClient,
    order_id: int,
) -> Order:
    resp = await client.get(f"orders/{order_id}")
    return normalize_order(resp.data)  # type: ignore[arg-type]


async def handle_search_orders(
    client: WooCommerceClient,
    *,
    search: str | None = None,
    status: str | None = None,
    after: str | None = None,
    before: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> PaginatedResponse[Order]:
    """Search/filter orders.

    WooCommerce ``search`` param matches against order numbers, billing
    names, and billing email.  Additional filters narrow results further.
    """
    params: dict = {"page": max(page, 1), "per_page": _clamp_per_page(per_page)}
    if search:
        params["search"] = search
    if status:
        params["status"] = status
    if after:
        params["after"] = after
    if before:
        params["before"] = before

    resp = await client.get("orders", params=params)
    orders = [normalize_order(o) for o in resp.data]  # type: ignore[union-attr]
    return PaginatedResponse(
        data=orders,
        page=params["page"],
        per_page=params["per_page"],
        total=resp.total,
        total_pages=resp.total_pages,
    )
