# Agent Capabilities

This document describes what an AI agent connected through the Agent Commerce Connector can and cannot do.

## The agent CAN

| Capability | Tool | Notes |
|---|---|---|
| List orders | `list_orders` | Filter by status, customer, date range; paginated |
| Get order details | `get_order` | Retrieve a single order by ID |
| Search/filter orders | `search_orders` | Search by text (order number, billing name/email) + filters |
| List products | `list_products` | Filter by search text, category, status; paginated |
| Get product details | `get_product` | Retrieve a single product by ID |
| Check inventory | `check_inventory` | Stock quantity, status, SKU, manage-stock flag |
| Use pagination | All list tools | Bounded `page` and `per_page` (1–100) |
| Receive structured errors | All tools | Machine-readable error codes (e.g., `NOT_FOUND`, `RATE_LIMITED`) |

All data is returned in a normalized, agent-friendly JSON format — not raw WooCommerce API output.

## The agent CANNOT

| Restriction | Reason |
|---|---|
| Create orders | Write operations not implemented — read-only by design |
| Modify orders | Read-only |
| Cancel / refund orders | Read-only |
| Create / update / delete products | Read-only |
| Modify inventory levels | Read-only |
| Modify customer information | Read-only |
| Access arbitrary WooCommerce endpoints | Only the 6 registered tools are available |
| Retrieve API credentials | Credentials are never returned through tool responses |
| Access other stores | The connector is bound to a single configured store URL |
| Make unlimited requests | Pagination is bounded; rate limits are respected |

## Why read-only?

The connector is intentionally limited to read operations because:

1. **Safety**: An AI agent should not be able to mutate merchant data without explicit human approval workflows.
2. **Scope**: The assignment requires reading commerce data, not managing it.
3. **Trust boundary**: Read-only access is the appropriate starting point for an integration that handles real business data.

Write capabilities could be added in the future behind explicit confirmation/approval mechanisms, but they are deliberately out of scope for this version.
