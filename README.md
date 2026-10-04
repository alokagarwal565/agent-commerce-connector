# Agent Commerce Connector (WooCommerce)

A private, production-grade Model Context Protocol (MCP) connector that enables AI agents (such as Agent Studio agents) to securely read commerce data from WooCommerce.

[![Tests](https://img.shields.io/badge/tests-30%20passed-brightgreen)](#running-tests)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![Protocol](https://img.shields.io/badge/MCP-FastMCP%20v1.24-purple)](https://modelcontextprotocol.io/)
[![Safety](https://img.shields.io/badge/safety-read--only-emerald)](#safety--capabilities)

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Safety & Capabilities](#safety--capabilities)
- [Exposed MCP Tools](#exposed-mcp-tools)
- [Authentication & Setup](#authentication--setup)
- [Quickstart](#quickstart)
- [Running Tests](#running-tests)
- [Interactive Demo](#interactive-demo)
- [Running as an MCP Server](#running-as-an-mcp-server)
- [Error Handling & Resilience](#error-handling--resilience)
- [Example Agent Workflows](#example-agent-workflows)
- [Assumptions & Limitations](#assumptions--limitations)
- [Documentation Index](#documentation-index)

---

## Overview

Modern AI agents need accurate, real-time access to e-commerce state — order statuses, inventory counts, product catalogs — without risking catastrophic unintended mutations (such as accidental order cancellations, refunds, or price changes).

**Agent Commerce Connector** solves this by providing:
- **Strictly Read-Only Surface**: 6 purpose-built tools for queries and search; zero mutation tools exposed.
- **Normalized Data Models**: Raw WooCommerce payloads are filtered and structured into clean, token-efficient Pydantic schemas.
- **Resilience Out-of-the-Box**: Transparent handling of rate limits (`429` with `Retry-After` parsing) and server blips (`5xx` exponential backoff).
- **FastMCP Protocol Support**: Ready to plug into any MCP client (Claude Desktop, Cursor, Agent Studio) over standard input/output (`stdio`) or SSE.
- **Dual-Mode Demo**: Run immediately with realistic synthetic fixtures without needing a live store, or connect your WooCommerce credentials for live operation.

---

## Architecture

```
Agent / Agent Studio / LLM
          │
          │ MCP stdio / SSE
          ▼
┌──────────────────────────────────────────────┐
│            MCP Server (FastMCP)              │
│  [list_orders, get_order, search_orders,     │
│   list_products, get_product, check_inv]     │
└──────────────────────┬───────────────────────┘
                       │ Validates input parameters
                       ▼
┌──────────────────────────────────────────────┐
│                Tool Handlers                 │
│  (app/tools/{orders,products,inventory}.py)  │
│  • Pydantic parameter validation             │
│  • Normalization to token-efficient schemas  │
│  • Standardized error envelopes              │
└──────────────────────┬───────────────────────┘
                       │ Calls client
                       ▼
┌──────────────────────────────────────────────┐
│              WooCommerceClient               │
│  (app/client/woo_client.py)                  │
│  • Basic Auth (Consumer Key & Secret)        │
│  • Retry-After header parsing (HTTP 429)     │
│  • Exponential backoff (HTTP 5xx)            │
│  • Pagination extraction (X-WP-Total*)       │
└──────────────────────┬───────────────────────┘
                       │ HTTPS (REST API v3)
                       ▼
┌──────────────────────────────────────────────┐
│         WooCommerce Store REST API           │
│         https://store.example.com/           │
└──────────────────────────────────────────────┘
```

For detailed sequence diagrams, rate-limiting state machines, and threat models, see [docs/architecture.md](docs/architecture.md).

---

## Safety & Capabilities

This connector enforces a hard security boundary between the AI agent and the merchant store.

### What the Agent CAN Do
- Query order lists filtered by status, customer ID, or date range.
- Retrieve full itemized details for specific orders.
- Search orders using arbitrary keywords or customer emails.
- Browse catalog products by category, status, or search term.
- Check live stock quantity, stock status (`instock`, `outofstock`, `onbackorder`), and low-stock thresholds.

### What the Agent CANNOT Do
- Create, modify, cancel, or delete orders.
- Issue refunds or adjust order payment states.
- Change product titles, descriptions, categories, or prices.
- Alter inventory levels or modify stock management flags.
- Access raw customer billing addresses or credit card tokens.

For a full capabilities matrix and design rationale, see [docs/agent-capabilities.md](docs/agent-capabilities.md) and [docs/design-decisions.md](docs/design-decisions.md).

---

## Exposed MCP Tools

All tools return JSON strings adhering to the MCP tool protocol.

### 1. `list_orders`
Lists orders with pagination and filtering.
- **Parameters**:
  - `page` *(int, default: 1)*: Page number.
  - `per_page` *(int, default: 20, max: 100)*: Orders per page.
  - `status` *(string, optional)*: Filter by status (`pending`, `processing`, `completed`, `on-hold`, `cancelled`, `refunded`, `failed`).
  - `customer` *(int, optional)*: Filter by customer ID.
  - `after` *(string, optional)*: ISO 8601 date string (e.g. `2025-01-01T00:00:00Z`).
  - `before` *(string, optional)*: ISO 8601 date string.
- **Output**: `PaginatedResponse[Order]`

### 2. `get_order`
Fetches a single order by its WooCommerce ID.
- **Parameters**:
  - `order_id` *(int, required)*: The order ID.
- **Output**: `Order`

### 3. `search_orders`
Searches orders by keyword, customer details, status, or date range.
- **Parameters**:
  - `search` *(string, optional)*: Search term matching customer, product name, or note.
  - `status` *(string, optional)*: Order status filter.
  - `after` *(string, optional)*: Orders after ISO 8601 date.
  - `before` *(string, optional)*: Orders before ISO 8601 date.
  - `page` *(int, default: 1)*
  - `per_page` *(int, default: 20, max: 100)*
- **Output**: `PaginatedResponse[Order]`

### 4. `list_products`
Lists catalog products with optional filters.
- **Parameters**:
  - `page` *(int, default: 1)*
  - `per_page` *(int, default: 20, max: 100)*
  - `search` *(string, optional)*: Search keyword.
  - `category` *(int, optional)*: WooCommerce category ID.
  - `status` *(string, optional)*: Product status (e.g. `publish`, `draft`).
- **Output**: `PaginatedResponse[Product]`

### 5. `get_product`
Fetches complete product details by ID.
- **Parameters**:
  - `product_id` *(int, required)*: The product ID.
- **Output**: `Product`

### 6. `check_inventory`
Retrieves stock counts, management status, and SKU info. Can inspect a single product or list inventory across products filtered by stock status.
- **Parameters**:
  - `product_id` *(int, optional)*: Product ID to inspect.
  - `stock_status` *(string, optional)*: Filter by `instock`, `outofstock`, or `onbackorder`.
  - `page` *(int, default: 1)*
  - `per_page` *(int, default: 20, max: 100)*
- **Output**: `InventoryItem` (if `product_id` provided) or `PaginatedResponse[InventoryItem]`.

---

## Authentication & Setup

The connector uses WooCommerce REST API v3 authentication via HTTP Basic Auth (Consumer Key and Consumer Secret) over HTTPS.

### Generating WooCommerce Keys
1. In your WordPress admin, navigate to **WooCommerce > Settings > Advanced > REST API**.
2. Click **Add key**.
3. Set the Description (e.g., `Agent Studio Connector`).
4. Set Permissions to **Read** *(Recommended: follows least privilege)*.
5. Click **Generate API key** and copy the `Consumer Key` (`ck_...`) and `Consumer Secret` (`cs_...`).

### Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` with your store configuration:
```ini
WOOCOMMERCE_STORE_URL=https://your-store-domain.com
WOOCOMMERCE_CONSUMER_KEY=ck_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
WOOCOMMERCE_CONSUMER_SECRET=cs_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
REQUEST_TIMEOUT_SECONDS=15
MAX_RETRIES=3
MAX_PER_PAGE=100
```

> **Security Note**: Credentials are loaded via `pydantic-settings` using `SecretStr`. They are never logged or exposed in string representations or stack traces.

---

## Quickstart

### 1. Installation
Requires Python 3.10+.

```bash
# Clone the repository
git clone https://github.com/your-username/agent-commerce-connector.git
cd agent-commerce-connector

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install package with development dependencies
pip install -e ".[dev]"
```

---

## Running Tests

The test suite includes 30 unit and integration tests covering configuration validation, error codes, HTTP retry behavior, normalization, and tool schemas. All tests run against mocked responses via `respx` and do not require live WooCommerce credentials.

```bash
pytest -v
```

Expected output:
```text
======================= 30 passed, 1 warning in 27s ========================
```

---

## Interactive Demo

The connector includes an interactive demo script (`scripts/demo.py`) that demonstrates all 6 tool operations.

- If `.env` is configured with credentials, it queries your **live** store.
- If `.env` is not present, it automatically uses **synthetic fixtures** (`tests/fixtures/`) to demonstrate normalization without setup.

Run the demo:
```bash
python scripts/demo.py
```

---

## Running as an MCP Server

To start the connector as a standard MCP server communicating over `stdio`:

```bash
python -m app.main
```

### Configuring in Claude Desktop or Agent Studio

Add the connector to your MCP client configuration (e.g. `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "woocommerce": {
      "command": "python",
      "args": ["-m", "app.main"],
      "cwd": "/path/to/agent-commerce-connector",
      "env": {
        "WOOCOMMERCE_STORE_URL": "https://your-store.com",
        "WOOCOMMERCE_CONSUMER_KEY": "ck_...",
        "WOOCOMMERCE_CONSUMER_SECRET": "cs_..."
      }
    }
  }
}
```

---

## Error Handling & Resilience

Errors are normalized into machine-readable structures returned to the agent:

```json
{
  "code": "RATE_LIMITED",
  "message": "WooCommerce rate limit exceeded. Retry after 10 seconds.",
  "retry_after": 10
}
```

| HTTP Status | Connector Code | Behavior |
|---|---|---|
| `401` | `AUTHENTICATION_ERROR` | Fails fast; check Consumer Key / Secret. |
| `403` | `AUTHORIZATION_ERROR` | Fails fast; check key permissions. |
| `404` | `NOT_FOUND` | Fails fast; resource does not exist. |
| `422` | `VALIDATION_ERROR` | Fails fast; invalid query parameter. |
| `429` | `RATE_LIMITED` | Reads `Retry-After` header, sleeps and retries up to `max_retries`. |
| `5xx` | `UPSTREAM_ERROR` | Retries with exponential backoff (1s, 2s, 4s). |
| Timeout | `TIMEOUT` | Request timed out after configured duration. |

---

## Example Agent Workflows

Here are example user queries and how the agent utilizes the connector tools:

1. **"Are there any orders waiting to be processed?"**
   - Agent invokes: `list_orders(status="processing", per_page=10)`
   - Agent summarizes customer emails, item quantities, and order totals.

2. **"Customer Jane Doe (jane.doe@example.test) is asking about her order status."**
   - Agent invokes: `search_orders(search="jane.doe@example.test")`
   - Agent finds order ID `1001`, checks status (`processing`), and replies with the ETA and line items.

3. **"Do we have enough Running Shoes in stock for an order of 30 units?"**
   - Agent invokes: `check_inventory(product_id=10)`
   - Connector returns `{ stock_quantity: 25, stock_status: "instock" }`
   - Agent reports: "Only 25 units currently in stock; 30 units cannot be fulfilled immediately."

---

## Assumptions & Limitations

### Assumptions
1. **API Version**: The connector assumes WooCommerce REST API v3 (`/wp-json/wc/v3`), enabled by default in all modern WooCommerce installations (v3.5+).
2. **Transport Security (HTTPS)**: Assumes production stores enforce HTTPS. WooCommerce Basic Auth transmits encoded API keys, which requires SSL/TLS encryption.
3. **Permissions**: Assumes the API key has at least `Read` permissions under **WooCommerce > Settings > Advanced > REST API**.
4. **Agent Transport**: Assumes the AI agent platform (Agent Studio, Claude Desktop, Cursor) supports standard Model Context Protocol (MCP) clients over `stdio` or SSE.

### Limitations
1. **Strictly Read-Only**: By design, mutation operations (creating/cancelling orders, changing product prices, issuing refunds, updating stock levels) are omitted to safeguard merchant operations against LLM hallucinations or unauthorized actions.
2. **Pass-Through Architecture (No Local Cache)**: To ensure 100% data consistency, the connector acts as a direct pass-through to WooCommerce. High-frequency queries rely directly on store performance and rate limits.
3. **Single Store Instance**: Configured for a single merchant store per connector instance via environment variables. Multi-tenant routing would require running separate container instances per merchant.
4. **Inventory Coupled to Product Resource**: Because WooCommerce manages inventory fields directly within the `/products` endpoint rather than having a distinct `/inventory` API, inventory checks inspect the underlying product schema.

---

## Documentation Index

- [docs/architecture.md](docs/architecture.md): Architectural components, data flow diagrams, security boundaries.
- [docs/agent-capabilities.md](docs/agent-capabilities.md): Agent CAN / CANNOT matrix and read-only rationale.
- [docs/design-decisions.md](docs/design-decisions.md): Why WooCommerce, FastMCP over REST, client encapsulation, and out-of-scope items.
- [scripts/demo.py](scripts/demo.py): Standalone demo runner.

