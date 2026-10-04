"""MCP server exposing WooCommerce read-only tools.

Each tool returns a JSON string (MCP protocol).  Errors are returned as
structured JSON error objects — never raised as exceptions to the agent.
"""

from __future__ import annotations

import json
import logging

from mcp.server.fastmcp import FastMCP

from app.client.woo_client import WooCommerceClient
from app.config import Settings
from app.errors import CONFIGURATION_ERROR, ConnectorError

logger = logging.getLogger(__name__)

mcp = FastMCP("agent-commerce-connector")

# -- Lazy singleton -----------------------------------------------------------
# Initialized on first tool call so the server can start even without env vars
# (useful for ``mcp dev`` / schema introspection).

_client: WooCommerceClient | None = None


def _get_client() -> WooCommerceClient:
    global _client
    if _client is None:
        try:
            settings = Settings()  # type: ignore[call-arg]
        except Exception as exc:
            raise ConnectorError(
                CONFIGURATION_ERROR,
                f"Missing or invalid configuration: {exc}",
            ) from exc
        _client = WooCommerceClient(settings)
        logger.info("woo_client_initialized store=%s", settings.woocommerce_store_url)
    return _client


def _ok(result: object) -> str:
    """Serialize a Pydantic model (or list/dict) to JSON."""
    if hasattr(result, "model_dump"):
        return json.dumps(result.model_dump(), default=str)
    return json.dumps(result, default=str)


def _err(exc: ConnectorError) -> str:
    return json.dumps(exc.to_dict())


# -- Tools --------------------------------------------------------------------

@mcp.tool()
async def list_orders(
    page: int = 1,
    per_page: int = 20,
    status: str | None = None,
    customer: int | None = None,
    after: str | None = None,
    before: str | None = None,
) -> str:
    """Lists WooCommerce orders with optional filters.

    This tool is read-only and cannot create, update, cancel, refund, or
    delete orders.

    Args:
        page: Page number (>= 1, default 1).
        per_page: Results per page, 1-100 (default 20).
        status: Filter by status (pending, processing, on-hold, completed,
                cancelled, refunded, failed, trash).
        customer: Filter by customer ID.
        after: Return orders placed after this ISO-8601 date.
        before: Return orders placed before this ISO-8601 date.
    """
    from app.tools.orders import handle_list_orders

    try:
        result = await handle_list_orders(
            _get_client(),
            page=page,
            per_page=per_page,
            status=status,
            customer=customer,
            after=after,
            before=before,
        )
        return _ok(result)
    except ConnectorError as exc:
        return _err(exc)


@mcp.tool()
async def get_order(order_id: int) -> str:
    """Retrieves a single WooCommerce order by its ID.

    This tool is read-only and cannot modify the order.

    Args:
        order_id: The unique order ID.
    """
    from app.tools.orders import handle_get_order

    try:
        result = await handle_get_order(_get_client(), order_id)
        return _ok(result)
    except ConnectorError as exc:
        return _err(exc)


@mcp.tool()
async def search_orders(
    search: str | None = None,
    status: str | None = None,
    after: str | None = None,
    before: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> str:
    """Searches WooCommerce orders by text, status, and/or date range.

    The ``search`` parameter matches against order number, billing name,
    and billing email.  This tool is read-only.

    Args:
        search: Free-text search string.
        status: Filter by order status.
        after: Return orders placed after this ISO-8601 date.
        before: Return orders placed before this ISO-8601 date.
        page: Page number (default 1).
        per_page: Results per page, 1-100 (default 20).
    """
    from app.tools.orders import handle_search_orders

    try:
        result = await handle_search_orders(
            _get_client(),
            search=search,
            status=status,
            after=after,
            before=before,
            page=page,
            per_page=per_page,
        )
        return _ok(result)
    except ConnectorError as exc:
        return _err(exc)


@mcp.tool()
async def list_products(
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
    category: int | None = None,
    status: str | None = None,
) -> str:
    """Lists WooCommerce products with optional filters.

    This tool is read-only and cannot create, update, or delete products.

    Args:
        page: Page number (default 1).
        per_page: Results per page, 1-100 (default 20).
        search: Search products by name.
        category: Filter by category ID.
        status: Filter by product status (publish, draft, pending, private).
    """
    from app.tools.products import handle_list_products

    try:
        result = await handle_list_products(
            _get_client(),
            page=page,
            per_page=per_page,
            search=search,
            category=category,
            status=status,
        )
        return _ok(result)
    except ConnectorError as exc:
        return _err(exc)


@mcp.tool()
async def get_product(product_id: int) -> str:
    """Retrieves a single WooCommerce product by its ID.

    This tool is read-only and cannot modify the product.

    Args:
        product_id: The unique product ID.
    """
    from app.tools.products import handle_get_product

    try:
        result = await handle_get_product(_get_client(), product_id)
        return _ok(result)
    except ConnectorError as exc:
        return _err(exc)


@mcp.tool()
async def check_inventory(
    product_id: int | None = None,
    stock_status: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> str:
    """Checks inventory levels for WooCommerce products.

    When ``product_id`` is provided, returns stock info for that single
    product.  Otherwise lists products optionally filtered by stock status.

    Returns: product ID, name, SKU, stock quantity, stock status,
    manage-stock flag, and low-stock threshold.

    This tool is read-only — it cannot modify inventory levels.

    Args:
        product_id: Check a specific product (optional).
        stock_status: Filter by stock status: instock, outofstock,
                      onbackorder (optional, ignored when product_id is set).
        page: Page number (default 1, ignored when product_id is set).
        per_page: Results per page, 1-100 (default 20, ignored when
                  product_id is set).
    """
    from app.tools.inventory import handle_check_inventory

    try:
        result = await handle_check_inventory(
            _get_client(),
            product_id=product_id,
            stock_status=stock_status,
            page=page,
            per_page=per_page,
        )
        return _ok(result)
    except ConnectorError as exc:
        return _err(exc)
