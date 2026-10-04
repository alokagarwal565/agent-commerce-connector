# Architecture

## System Overview

```
Agent / Agent Studio
        │
        ▼
┌─────────────────────────┐
│   MCP Server (FastMCP)  │  ← stdio / SSE transport
│                         │
│   ┌───────────────────┐ │
│   │   Tool Handlers   │ │  ← input validation + response normalization
│   └────────┬──────────┘ │
│            │            │
│   ┌────────▼──────────┐ │
│   │ WooCommerce Client│ │  ← HTTP, auth, retry, rate-limit
│   └────────┬──────────┘ │
│            │            │
│   ┌────────▼──────────┐ │
│   │     Settings      │ │  ← env-based configuration (SecretStr)
│   └───────────────────┘ │
└────────────┬────────────┘
             │
             ▼
   WooCommerce REST API v3
```

## Components

### MCP Server (`app/server.py`)

- Built on `FastMCP` from the MCP Python SDK.
- Registers 6 read-only tools with agent-facing descriptions.
- Handles tool dispatch and JSON serialization.
- Catches `ConnectorError` and returns structured error JSON — never throws raw exceptions to the agent.

### Tool Handlers (`app/tools/`)

- Pure async functions: `handle_list_orders`, `handle_get_order`, etc.
- Validate and clamp input parameters (e.g., `per_page` bounded to 1–100).
- Call the WooCommerce client and normalize raw responses into Pydantic models.
- Independently testable — no dependency on MCP framework.

### WooCommerce Client (`app/client/woo_client.py`)

- The **only** module that knows WooCommerce HTTP details.
- Uses `httpx.AsyncClient` with HTTP Basic Auth.
- Handles retries (429 + 5xx), exponential backoff, `Retry-After` headers.
- Extracts pagination metadata from `X-WP-Total` / `X-WP-TotalPages` headers.
- Returns `WooResponse(data, total, total_pages)`.

### Models (`app/models/`)

- Pydantic models defining the agent-facing schema.
- `normalize_*()` functions map raw WooCommerce JSON → clean models.
- Internal WooCommerce fields (`meta_data`, `_links`, tax breakdowns) are dropped.

### Configuration (`app/config.py`)

- `pydantic-settings` loaded from environment variables / `.env` file.
- Credentials stored as `SecretStr` — never appear in logs or `repr()`.
- Validated at load time; fast-fail on missing or invalid values.

### Errors (`app/errors.py`)

- `ConnectorError(code, message)` with machine-readable codes.
- HTTP status → error code mapping (`401→AUTHENTICATION_ERROR`, `429→RATE_LIMITED`, etc.).

## Data Flow

1. Agent invokes an MCP tool (e.g., `list_orders(status="processing")`).
2. `app/server.py` dispatches to the tool handler.
3. Tool handler validates params, calls `WooCommerceClient.get()`.
4. Client builds URL, adds auth, sends HTTP request.
5. On success: client returns `WooResponse`; handler normalizes to Pydantic model.
6. On error: client raises `ConnectorError`; server catches and serializes.
7. JSON string is returned to the agent.

## Rate-Limit Flow

```
Request → 429?
           ├─ Yes → Attempt < max_retries?
           │         ├─ Yes → sleep(Retry-After) → retry
           │         └─ No  → raise RATE_LIMITED
           └─ No → 5xx?
                    ├─ Yes → Attempt < max_retries?
                    │         ├─ Yes → sleep(2^attempt) → retry
                    │         └─ No  → raise UPSTREAM_ERROR
                    └─ No → 4xx?
                             ├─ Yes → raise (NOT_FOUND / AUTH / etc.)
                             └─ No → return success
```

## Security Boundaries

- Credentials: env-only, `SecretStr`, never logged or returned.
- Store URL: configured once, not overridable per-request (no SSRF).
- Tool surface: read-only — no create/update/delete operations exposed.
- Response normalization: internal WooCommerce fields stripped before reaching the agent.
