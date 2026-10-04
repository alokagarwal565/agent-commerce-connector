"""Tests for order tool handlers."""

from __future__ import annotations

import httpx
import pytest
import respx

from app.tools.orders import handle_get_order, handle_list_orders, handle_search_orders
from tests.conftest import BASE_API, load_fixture


@pytest.mark.asyncio
async def test_list_orders(client, mock_api):
    data = load_fixture("orders.json")
    mock_api.get(f"{BASE_API}/orders").mock(
        return_value=httpx.Response(
            200, json=data, headers={"X-WP-Total": "3", "X-WP-TotalPages": "1"}
        )
    )
    result = await handle_list_orders(client)
    assert len(result.data) == 3
    assert result.total == 3
    assert result.data[0].id == 1001
    assert result.data[0].status == "processing"
    assert len(result.data[0].items) == 2


@pytest.mark.asyncio
async def test_list_orders_with_status_filter(client, mock_api):
    data = [load_fixture("orders.json")[1]]  # completed order
    route = mock_api.get(f"{BASE_API}/orders").mock(
        return_value=httpx.Response(200, json=data)
    )
    result = await handle_list_orders(client, status="completed")
    assert len(result.data) == 1
    assert result.data[0].status == "completed"
    # Verify the status param was sent
    assert route.calls[0].request.url.params["status"] == "completed"


@pytest.mark.asyncio
async def test_get_order(client, mock_api):
    data = load_fixture("order_single.json")
    mock_api.get(f"{BASE_API}/orders/1001").mock(
        return_value=httpx.Response(200, json=data)
    )
    order = await handle_get_order(client, 1001)
    assert order.id == 1001
    assert order.customer.id == 42
    assert order.customer.email == "jane.doe@example.test"
    assert order.note == "Please gift wrap"
    assert order.items[0].sku == "RS-001"


@pytest.mark.asyncio
async def test_search_orders(client, mock_api):
    data = load_fixture("orders.json")[:1]
    route = mock_api.get(f"{BASE_API}/orders").mock(
        return_value=httpx.Response(200, json=data)
    )
    result = await handle_search_orders(client, search="jane", status="processing")
    assert len(result.data) == 1
    assert route.calls[0].request.url.params["search"] == "jane"
    assert route.calls[0].request.url.params["status"] == "processing"


@pytest.mark.asyncio
async def test_pagination_clamping(client, mock_api):
    mock_api.get(f"{BASE_API}/orders").mock(
        return_value=httpx.Response(200, json=[])
    )
    result = await handle_list_orders(client, page=0, per_page=999)
    assert result.page == 1
    assert result.per_page == 100
