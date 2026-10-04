"""Tests for inventory tool handler."""

from __future__ import annotations

import httpx
import pytest
import respx

from app.tools.inventory import handle_check_inventory
from tests.conftest import BASE_API, load_fixture


@pytest.mark.asyncio
async def test_single_product_inventory(client, mock_api):
    data = load_fixture("product_single.json")
    mock_api.get(f"{BASE_API}/products/10").mock(
        return_value=httpx.Response(200, json=data)
    )
    item = await handle_check_inventory(client, product_id=10)
    # Returns InventoryItem, not PaginatedResponse
    assert item.product_id == 10
    assert item.stock_quantity == 25
    assert item.stock_status == "instock"
    assert item.manage_stock is True
    assert item.sku == "RS-001"
    assert item.low_stock_threshold == 5


@pytest.mark.asyncio
async def test_bulk_inventory(client, mock_api):
    data = load_fixture("products.json")
    mock_api.get(f"{BASE_API}/products").mock(
        return_value=httpx.Response(
            200, json=data, headers={"X-WP-Total": "4", "X-WP-TotalPages": "1"}
        )
    )
    result = await handle_check_inventory(client)
    assert len(result.data) == 4
    # Verify out-of-stock item
    water_bottle = [i for i in result.data if i.product_id == 12][0]
    assert water_bottle.stock_status == "outofstock"
    assert water_bottle.stock_quantity == 0


@pytest.mark.asyncio
async def test_inventory_stock_status_filter(client, mock_api):
    route = mock_api.get(f"{BASE_API}/products").mock(
        return_value=httpx.Response(200, json=[])
    )
    await handle_check_inventory(client, stock_status="outofstock")
    assert route.calls[0].request.url.params["stock_status"] == "outofstock"


@pytest.mark.asyncio
async def test_unmanaged_stock(client, mock_api):
    # Trail Backpack: manage_stock=false, stock_quantity=null
    data = load_fixture("products.json")[3]
    mock_api.get(f"{BASE_API}/products/13").mock(
        return_value=httpx.Response(200, json=data)
    )
    item = await handle_check_inventory(client, product_id=13)
    assert item.manage_stock is False
    assert item.stock_quantity is None
    assert item.low_stock_threshold is None
