"""Tests for product tool handlers."""

from __future__ import annotations

import httpx
import pytest
import respx

from app.tools.products import handle_get_product, handle_list_products
from tests.conftest import BASE_API, load_fixture


@pytest.mark.asyncio
async def test_list_products(client, mock_api):
    data = load_fixture("products.json")
    mock_api.get(f"{BASE_API}/products").mock(
        return_value=httpx.Response(
            200, json=data, headers={"X-WP-Total": "4", "X-WP-TotalPages": "1"}
        )
    )
    result = await handle_list_products(client)
    assert len(result.data) == 4
    assert result.data[0].name == "Running Shoes"
    assert result.data[0].categories == ["Footwear"]
    # Sale price present
    assert result.data[0].sale_price == "99.99"
    # No sale price → None
    assert result.data[1].sale_price is None


@pytest.mark.asyncio
async def test_list_products_search(client, mock_api):
    data = [load_fixture("products.json")[0]]
    route = mock_api.get(f"{BASE_API}/products").mock(
        return_value=httpx.Response(200, json=data)
    )
    result = await handle_list_products(client, search="running")
    assert len(result.data) == 1
    assert route.calls[0].request.url.params["search"] == "running"


@pytest.mark.asyncio
async def test_get_product(client, mock_api):
    data = load_fixture("product_single.json")
    mock_api.get(f"{BASE_API}/products/10").mock(
        return_value=httpx.Response(200, json=data)
    )
    product = await handle_get_product(client, 10)
    assert product.id == 10
    assert product.sku == "RS-001"
    assert product.stock_quantity == 25
    assert product.stock_status == "instock"
    assert product.categories == ["Footwear"]


@pytest.mark.asyncio
async def test_product_multiple_categories(client, mock_api):
    data = load_fixture("products.json")[2]  # Water Bottle — 2 categories
    mock_api.get(f"{BASE_API}/products/12").mock(
        return_value=httpx.Response(200, json=data)
    )
    product = await handle_get_product(client, 12)
    assert product.categories == ["Accessories", "Hydration"]
