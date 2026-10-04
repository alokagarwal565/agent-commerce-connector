"""Tests for MCP tool registration and schema."""

from __future__ import annotations

import json

import pytest

from app.server import mcp


def test_all_tools_registered():
    """All 6 read-only tools must be registered."""
    tools = mcp._tool_manager._tools  # FastMCP internal registry
    names = set(tools.keys())
    expected = {
        "list_orders",
        "get_order",
        "search_orders",
        "list_products",
        "get_product",
        "check_inventory",
    }
    assert expected.issubset(names), f"Missing tools: {expected - names}"


def test_no_write_tools():
    """The connector must NOT expose any mutation tools."""
    tools = mcp._tool_manager._tools
    forbidden = {
        "create_order",
        "update_order",
        "delete_order",
        "refund_order",
        "create_product",
        "update_product",
        "delete_product",
        "update_inventory",
    }
    found = forbidden & set(tools.keys())
    assert not found, f"Write tools found: {found}"


def test_tool_count():
    """Exactly 6 tools — no hidden extras."""
    tools = mcp._tool_manager._tools
    assert len(tools) == 6
