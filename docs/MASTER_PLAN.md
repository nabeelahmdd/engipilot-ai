# CommercePilot AI — Master Plan v1.0

## Mission

Build **one** substantial e-commerce application showcasing professional backend engineering **and** production-oriented AI, with every layer implemented and tested manually. The backend is intentionally built first; AI agents use its validated service contracts. Git history from EngiPilot is preserved.

## Non-negotiable project rules

- Python 3.12, `uv` for packages and lockfile; never mix `pip install` into the project environment.
- A modular monolith, not premature microservices or six copy-pasted agent backends.
- PostgreSQL as business source of truth; external DummyJSON is optional fixture data.
- No real payment processing, real refunds, shipment carriers, or unsolicited external messages.
- No model-generated raw SQL or arbitrary execution of model output.
- Business decisions (price, inventory, ownership, refunds) are **deterministic Python**, not LLM authority.
- New dependencies only when needed by the current phase; new folders only when they contain working code.
- One feature at a time, tests and acceptance proof before progress is checked off.
- Manual code and package installation by the owner. Assistant guides and reviews; no prebuilt ZIP or bulk-generated application.

## Backend phases — implement BEFORE AI

### B0 Repository pivot [CURRENT]
- Replace old EngiPilot tree and branding with CommercePilot metadata/docs.
- Preserve prior Git history; use PR, not force-push to `main`.
- Acceptance: diff clearly replaces old code; PR review; manual repository rename; clean local `uv sync` and import.

### B1 API foundation
- `uv add fastapi "uvicorn[standard]" pydantic-settings`, dev packages as needed.
- App factory, environment settings, `GET /api/v1/health`, structured error envelope, correlation IDs.
- Unit tests; run `uv run pytest -q` and `uv run ruff check .`.
- Gate: health returns expected JSON in tests, no secrets in logs.

### B2 Database and boundaries
- Add SQLAlchemy 2, asyncpg, Alembic and PostgreSQL Docker service.
- Async session setup, migrations, repository and domain service seams.
- Gate: empty database migrate-up, migrations consistent, rollback verified, DB integration test.

### B3 Catalog API
- Product, category, stock, price models; read endpoints, pagination/filter/search, stable errors.
- Optional data seed from DummyJSON after validation and provenance rules.
- Gate: product CRUD where authorized, paginated listing, invalid input, no N+1 baseline.

### B4 Cart API
- Per-user cart, add/remove/update items, quantity validation, price calculated server-side.
- Gate: cart ownership, concurrency, duplicate mutation and invalid-stock tests.

### B5 Simulated orders
- Simulated checkout/order creation, order lifecycle and read-only status; no financial transaction.
- Gate: atomic inventory mutation, rollback, idempotent request key and valid state machine.

### B6 Identity, authorization and audit
- Authentication approach chosen only when backend flows demand it; do not reinstate obsolete company/org models.
- Actor resolution, object-level access, audit trail and data boundaries.
- Gate: unauthorized and cross-user access rejected for ALL write/read operations.

## AI phases — extend the existing backend, not a second business backend

### A1 LangChain, LLM and tools
- Model factory, role prompts, tool schemas and structured Pydantic outputs.
- Tools call domain services with authenticated actor context, not DB directly.
- Gate: tool selection benchmark, malformed argument rejection, deterministic policy validation.

### A2 LangGraph orchestration
- Nodes, shared typed state, conditional routes, limits, checkpoints, retries, human approval/resume.
- Gate: crash/resume + rejection paths, dangerous action never executes before explicit approval.

### A3 MCP
- MCP server adapter exposes approved domain operations; MCP client discovers/calls with schema validation.
- Gate: tool discovery and round trip; MCP cannot bypass authorization enforced by domain services.

### A4 RAG
- Ingest approved product FAQs/policies, chunk, embed, retrieve, rerank and attribute source/version.
- Gate: a fixed evaluation set for retrieval relevance, unsupported-answer refusal and citations.

### A5 Multi-agent
- Shopping, cart/order and support agents, with supervisor routing and explicit handoff contracts.
- Gate: cross-agent shared state, fan-out only when justified, bounded agent loops.

### A6 Production AI
- Eval datasets (tool calls, trajectories, RAG, policy), tracing, cost/latency metrics, error paths.
- Prompt-injection and PII protection, fallback paths, rate/time budgets, test isolation.
- Gate: CI regression suite with score thresholds, alertable failures and cost per successful task.

### F Final demonstration
- Customer: “Compare phones within budget, add chosen one on confirmation, place a simulated order, and answer return policy with citations.”
- Verify authorization, product state, persistence, HITL, multi-agent trace and regression report.
- Gate: fresh-clone runbook reproducible, clear architecture/deployment limitations, PR merged.

## Suggested learning sequence

`domain logic → HTTP APIs → DB & transactions → validated tools → LangChain → LangGraph → MCP → RAG → multi-agent → evals & observability`

## Estimates (not commitments)

Backend adds work beyond the previous mock-API-only design. Plan a rough **120–200 focused hours** for manually learning and implementing all layers; refine estimates after B2.

## Definition of done for a phase

1. Code committed in feature branch and reviewed.
2. Tests pass and negative/abuse cases are covered.
3. API contracts / diagrams / decisions updated.
4. `docs/STATUS.md` records command and evidence.
5. `docs/HANDOFF.md` tells the next session exactly what to do.
