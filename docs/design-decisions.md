# Design Decisions

## 1. Why WooCommerce

WooCommerce was selected from the available options (Freshdesk, Zoho Inventory, WooCommerce, Unicommerce) because:

- **Well-documented REST API** (v3) with stable, publicly documented endpoints.
- **Simple authentication** — API key/secret via HTTP Basic Auth. No OAuth dance needed.
- **Rich data model** — orders, products, customers, and inventory are all available.
- **Free development stores** are easy to create for testing.

## 2. Why read-only

The connector exposes only `GET` operations. No create, update, or delete tools exist — not even behind a flag.

**Rationale**: An AI agent that can mutate real commerce data (cancel orders, change prices, zero out inventory) is a significant operational risk. Read-only access is the correct starting point. Write access should only be added with explicit human-in-the-loop confirmation.

## 3. Why MCP (not a REST API)

The assignment targets Agent Studio, which uses MCP for tool integration. Building a FastAPI REST wrapper would add a layer that an MCP-native agent can't directly consume.

FastMCP provides built-in stdio and SSE transports — no additional HTTP server needed.

## 4. Why the client layer is separate from tools

The WooCommerce HTTP client (`woo_client.py`) is isolated from tool definitions for three reasons:

1. **Testability**: Tools can be tested with a mocked client; the client can be tested independently against mocked HTTP.
2. **Single responsibility**: HTTP details (auth, retries, URL construction) stay in one place.
3. **Replaceability**: Swapping WooCommerce for another platform means replacing the client, not the tool layer.

## 5. How rate limiting is handled

- **429 responses**: Read `Retry-After` header (default 10s), sleep, retry up to `max_retries`.
- **5xx responses**: Exponential backoff (1s, 2s, 4s), retry up to `max_retries`.
- **4xx responses** (except 429): Never retried — these are client errors.
- **Timeouts**: Never retried — could indicate network issues that retrying would worsen.
- **Bounded**: Maximum `max_retries` attempts (default 3). No infinite loops.

## 6. How sensitive data is protected

- Credentials use `pydantic.SecretStr` — never appear in `repr()`, `str()`, or logs.
- `.env` is in `.gitignore`.
- Logging never emits auth headers or API keys.
- WooCommerce responses are normalized before reaching the agent — internal metadata is stripped.

## 7. Response normalization

Raw WooCommerce JSON contains 50+ fields per order, many irrelevant to an agent (tax line items, `meta_data`, `_links`, refund details). The connector normalizes to a focused schema:

- Orders: id, status, currency, total, customer (id + email), items, dates, payment method, note.
- Products: id, name, slug, status, sku, prices, stock info, categories, date.
- Inventory: product_id, name, sku, stock_quantity, stock_status, manage_stock, low_stock_threshold.

This gives agents enough data to answer useful questions without information overload.

## 8. What was deliberately left out

| Feature | Why excluded |
|---|---|
| OAuth flow | WooCommerce API keys are simpler and sufficient for a server-to-server connector |
| Customers endpoint | Not needed for the core order/product/inventory scope |
| Coupons, refunds, reports | Out of scope — adds complexity without demonstrating new patterns |
| Caching | Adds statefulness and invalidation complexity; not needed for this scope |
| Database | The connector is stateless — all data comes from WooCommerce |
| Frontend / dashboard | Would be infrastructure for its own sake; the MCP interface is the deliverable |
| WebSocket transport | stdio and SSE cover Agent Studio use cases |
