"""Product tool handlers – validation, WooCommerce call, normalization."""

from __future__ import annotations

from app.client.woo_client import WooCommerceClient
from app.models.common import PaginatedResponse
from app.models.products import Product, normalize_product


def _clamp_per_page(per_page: int) -> int:
    return max(1, min(per_page, 100))


async def handle_list_products(
    client: WooCommerceClient,
    *,
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
    category: int | None = None,
    status: str | None = None,
) -> PaginatedResponse[Product]:
    params: dict = {"page": max(page, 1), "per_page": _clamp_per_page(per_page)}
    if search:
        params["search"] = search
    if category is not None:
        params["category"] = category
    if status:
        params["status"] = status

    resp = await client.get("products", params=params)
    products = [normalize_product(p) for p in resp.data]  # type: ignore[union-attr]
    return PaginatedResponse(
        data=products,
        page=params["page"],
        per_page=params["per_page"],
        total=resp.total,
        total_pages=resp.total_pages,
    )


async def handle_get_product(
    client: WooCommerceClient,
    product_id: int,
) -> Product:
    resp = await client.get(f"products/{product_id}")
    return normalize_product(resp.data)  # type: ignore[arg-type]
