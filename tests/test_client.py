"""Tests for the WooCommerce HTTP client — error handling, retries, rate limits."""

from __future__ import annotations

import httpx
import pytest
import respx

from app.errors import (
    AUTHENTICATION_ERROR,
    AUTHORIZATION_ERROR,
    NOT_FOUND,
    RATE_LIMITED,
    TIMEOUT,
    UPSTREAM_ERROR,
    ConnectorError,
)
from tests.conftest import BASE_API


# -- Success ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_successful_get(client, mock_api):
    mock_api.get(f"{BASE_API}/orders").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": 1}],
            headers={"X-WP-Total": "1", "X-WP-TotalPages": "1"},
        )
    )
    resp = await client.get("orders")
    assert resp.data == [{"id": 1}]
    assert resp.total == 1
    assert resp.total_pages == 1


# -- Client errors (no retry) ------------------------------------------------


@pytest.mark.asyncio
async def test_401_authentication_error(client, mock_api):
    mock_api.get(f"{BASE_API}/orders").mock(
        return_value=httpx.Response(401, json={"message": "Consumer key is invalid."})
    )
    with pytest.raises(ConnectorError) as exc_info:
        await client.get("orders")
    assert exc_info.value.code == AUTHENTICATION_ERROR


@pytest.mark.asyncio
async def test_403_authorization_error(client, mock_api):
    mock_api.get(f"{BASE_API}/orders").mock(
        return_value=httpx.Response(403, json={"message": "Forbidden."})
    )
    with pytest.raises(ConnectorError) as exc_info:
        await client.get("orders")
    assert exc_info.value.code == AUTHORIZATION_ERROR


@pytest.mark.asyncio
async def test_404_not_found(client, mock_api):
    mock_api.get(f"{BASE_API}/orders/999").mock(
        return_value=httpx.Response(404, json={"message": "Not found."})
    )
    with pytest.raises(ConnectorError) as exc_info:
        await client.get("orders/999")
    assert exc_info.value.code == NOT_FOUND


# -- Rate limit (429) --------------------------------------------------------


@pytest.mark.asyncio
async def test_429_retries_then_succeeds(client, mock_api):
    route = mock_api.get(f"{BASE_API}/orders")
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "0"}),
        httpx.Response(200, json=[{"id": 1}]),
    ]
    resp = await client.get("orders")
    assert resp.data == [{"id": 1}]
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_429_exhausts_retries(client, mock_api):
    # max_retries=2, so 3 total 429s should exceed
    mock_api.get(f"{BASE_API}/orders").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "0"})
    )
    with pytest.raises(ConnectorError) as exc_info:
        await client.get("orders")
    assert exc_info.value.code == RATE_LIMITED
    assert exc_info.value.retry_after is not None


# -- Server error (5xx) ------------------------------------------------------


@pytest.mark.asyncio
async def test_500_retries_then_succeeds(client, mock_api):
    route = mock_api.get(f"{BASE_API}/orders")
    route.side_effect = [
        httpx.Response(500),
        httpx.Response(200, json=[]),
    ]
    resp = await client.get("orders")
    assert resp.data == []
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_500_exhausts_retries(client, mock_api):
    mock_api.get(f"{BASE_API}/orders").mock(return_value=httpx.Response(500))
    with pytest.raises(ConnectorError) as exc_info:
        await client.get("orders")
    assert exc_info.value.code == UPSTREAM_ERROR


# -- Timeout ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeout_error(client, mock_api):
    mock_api.get(f"{BASE_API}/orders").mock(side_effect=httpx.ReadTimeout("timeout"))
    with pytest.raises(ConnectorError) as exc_info:
        await client.get("orders")
    assert exc_info.value.code == TIMEOUT
