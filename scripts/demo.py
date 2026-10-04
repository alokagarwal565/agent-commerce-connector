#!/usr/bin/env python
"""Demo script showing all 6 connector tools.

When WooCommerce credentials are configured in ``.env``, this calls the real
API.  Otherwise it uses synthetic fixture data to demonstrate the
normalization pipeline.

Usage::

    python scripts/demo.py          # auto-detects mode
    python scripts/demo.py --mock   # force mock mode
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.inventory import normalize_inventory
from app.models.orders import normalize_order
from app.models.products import normalize_product

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def _pretty(obj) -> str:
    if hasattr(obj, "model_dump"):
        return json.dumps(obj.model_dump(), indent=2, default=str)
    return json.dumps(obj, indent=2, default=str)


def _header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


async def run_live():
    """Run against a real WooCommerce store."""
    from app.client.woo_client import WooCommerceClient
    from app.config import Settings
    from app.tools.inventory import handle_check_inventory
    from app.tools.orders import handle_get_order, handle_list_orders, handle_search_orders
    from app.tools.products import handle_get_product, handle_list_products

    settings = Settings()  # type: ignore[call-arg]
    client = WooCommerceClient(settings)

    try:
        _header("list_orders (page=1, per_page=3)")
        result = await handle_list_orders(client, per_page=3)
        print(_pretty(result))

        if result.data:
            _header(f"get_order (order_id={result.data[0].id})")
            order = await handle_get_order(client, result.data[0].id)
            print(_pretty(order))

        _header("search_orders (status=processing)")
        result = await handle_search_orders(client, status="processing", per_page=3)
        print(_pretty(result))

        _header("list_products (page=1, per_page=3)")
        result = await handle_list_products(client, per_page=3)
        print(_pretty(result))

        if result.data:
            _header(f"get_product (product_id={result.data[0].id})")
            product = await handle_get_product(client, result.data[0].id)
            print(_pretty(product))

        _header("check_inventory (page=1, per_page=3)")
        result = await handle_check_inventory(client, per_page=3)
        print(_pretty(result))

    finally:
        await client.close()


def run_mock():
    """Demonstrate normalization using synthetic fixtures."""
    _header("MOCK MODE — using synthetic fixture data")

    orders = json.loads((FIXTURES / "orders.json").read_text())
    _header("list_orders — normalized output (3 synthetic orders)")
    for raw in orders:
        print(_pretty(normalize_order(raw)))

    single_order = json.loads((FIXTURES / "order_single.json").read_text())
    _header("get_order — normalized output (order 1001)")
    print(_pretty(normalize_order(single_order)))

    products = json.loads((FIXTURES / "products.json").read_text())
    _header("list_products — normalized output (4 synthetic products)")
    for raw in products:
        print(_pretty(normalize_product(raw)))

    single_product = json.loads((FIXTURES / "product_single.json").read_text())
    _header("get_product — normalized output (product 10)")
    print(_pretty(normalize_product(single_product)))

    _header("check_inventory — normalized output")
    for raw in products:
        print(_pretty(normalize_inventory(raw)))


def main():
    force_mock = "--mock" in sys.argv

    if force_mock:
        run_mock()
        return

    try:
        from app.config import Settings
        settings = Settings()  # type: ignore[call-arg]

        key_val = settings.woocommerce_consumer_key.get_secret_value()
        if "example-store.test" in settings.woocommerce_store_url or "your_consumer_key" in key_val:
            print("Placeholder credentials detected in .env — running in MOCK mode.")
            run_mock()
            return

        print(f"Connecting to live WooCommerce store ({settings.woocommerce_store_url})...")
        asyncio.run(run_live())
    except Exception as exc:
        print(f"Live mode not available ({exc}) — running in MOCK mode.")
        run_mock()


if __name__ == "__main__":
    main()

