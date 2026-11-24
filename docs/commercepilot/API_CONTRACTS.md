# Planned Commerce APIs (not yet implemented)

Base prefix `/api/v1`.

| Phase | Endpoint | Purpose |
|---|---|---|
| B2 | `GET /products` | Search/filter/paginate catalog |
| B2 | `GET /products/{id}` | Product detail |
| B2 | `POST /products` | Authorized catalog create |
| B3 | `GET /cart` | Current user's cart |
| B3 | `POST /cart/items` | Add SKU and quantity |
| B3 | `PATCH /cart/items/{id}` | Change quantity |
| B3 | `DELETE /cart/items/{id}` | Remove line |
| B4 | `POST /orders` | Simulated order with idempotency key |
| B4 | `GET /orders/{id}` | Scoped order lookup |

Existing working endpoints `GET /api/v1/health` and `GET /api/v1/ready` remain.

### Invariants
- Money values fixed-precision; totals server-calculated.
- Inventory modifications transactional, with explicit stock checks.
- No arbitrary client-supplied owner in mutations.
- Agent/MCP tools call same validated service layer as REST endpoints.
- No real payment, refund, shipment or financial action.
