# Planned HTTP API contracts (not implemented)

Prefix: `/api/v1`. Responses will use explicit Pydantic schemas, stable errors and IDs.

| Capability | Endpoint | Notes |
|---|---|---|
| Health | `GET /health` | B1; independent of database |
| Catalog list | `GET /products?search=&category=&page=&limit=` | B3; bounded pagination |
| Catalog detail | `GET /products/{product_id}` | B3; 404 on missing |
| Cart read | `GET /cart` | B4; caller-scoped |
| Add to cart | `POST /cart/items` | B4; typed product + quantity |
| Update line | `PATCH /cart/items/{item_id}` | B4; ownership and quantity |
| Remove line | `DELETE /cart/items/{item_id}` | B4; idempotent semantics |
| Create order | `POST /orders` | B5; **simulated**, with idempotency |
| List orders | `GET /orders` | B5; caller-scoped |
| Order detail | `GET /orders/{order_id}` | B5; ownership enforcement |

No endpoint is present yet. Schemas, routes and response formats will be finalized and tested phase-by-phase.

## Domain invariant examples

- Product price and order total are server-computed in money-safe types.
- Inventory and checkout transition are atomic.
- Caller identity is verified; client cannot supply arbitrary owner for write.
- Only approved state transitions are allowed.
- LLM tool calls invoke these same domain services (not alternate raw DB queries).

## Future AI scenario

“Show the best phone within a budget, compare, add after approval, create a *simulated* order, and answer the return policy from evidence.” This end-to-end scenario must remain safe and testable offline.
