# CommercePilot AI — Master Implementation Plan v1.2

## Locked product scope
One real FastAPI + PostgreSQL e-commerce backend first, then comprehensive AI agent integration. No live payment/refund/shipment actions. User manually types and learns each package, directory and code change; assistant guides in small verified stages. Use `uv`, `pyproject.toml`, committed `uv.lock`, and the existing `src/engipilot_ai` package until a deliberate technical rename.

## Migration decision (M0)
- Keep: Python package, FastAPI app factory, Pydantic config, async DB/core, user/auth service/models/tokens, PostgreSQL, Alembic revision history, Docker/Compose, React scaffold, CI, dev scripts, tests and lockfiles.
- Retire: engineering-only `modules/organizations`, `modules/projects`, organization/project-specific tests and outdated product-specific docs.
- Update: ORM model registry, User model relationships, UI/API branding and matching tests.
- Add: guarded, **forward-only when legacy tables are empty** Alembic revision for retiring old tables. Never rewrite historical revisions.
- Preserve GitHub repo and internal import name `engipilot-ai` / `engipilot_ai` for now; future rename optional with lockfile, Docker, migrations and imports coordinated.
- Gate: review PR diff, ensure security/core/deployment preserved, run tests and migration on clean/legacy-populated fixtures. Do not merge if baseline or migration fails.

## Backend phases
| Phase | Deliverable | Exit test |
|---|---|---|
| B1 — Baseline | Current auth, health, async database and CI validated | `uv sync --locked`, Ruff, mypy, pytest, Alembic check + deployment smoke |
| B2 — Catalog | Product, category, inventory, price, search/filter/pagination | CRUD and validation tests, database indices and no-N+1 baseline |
| B3 — Cart | Authenticated customer cart, add/update/delete | Ownership, quantities, price recalculation, race-condition tests |
| B4 — Orders | Simulated checkout, inventory change, order state transitions | Atomic transaction, idempotency and rollback tests |
| B5 — Domain hardening | Error schemas, object access, rate limiting, audited actions | Cross-user denial and abuse suite |

## AI phases
| Phase | Deliverable | Exit test |
|---|---|---|
| A1 — LangChain | Model factory, prompt templates, structured output, typed tools | Correct tool routing, schema-invalid and provider-failure tests |
| A2 — LangGraph | State graph, checkpoints, conditional edges, bounded loops, HITL | Pause/approve/reject, process restart and recovery tests |
| A3 — MCP | MCP server exposing existing backend services, client discovery | Schema, authorization, round-trip tests |
| A4 — RAG | Ingest approved product policy/FAQ, embeddings, hybrid retrieval, reranking | Retrieval/answer benchmark with citations |
| A5 — Multi-agent | Supervisor, catalog/cart/order/support agents, handoff contracts | Multi-agent trace, bounds and single-agent baseline comparison |
| A6 — Operational AI | Long-term memory, model routing, evals, observability, security, cost/latency | Regression gates, injection tests, redacted traces and budget metrics |
| F — Final | End-to-end shopping agent + simulated order + policy citation | Fresh clone/demo/test instructions and measurable acceptance report |

## Architectural constraints
- `HTTP → service → repository → DB`; `AI tool/MCP → same service`. Business truth and ownership rules stay in deterministic backend code.
- Data stores selected by access pattern: PostgreSQL transaction state; graph checkpoints; vector retrieval for knowledge; trace platform for operational signals.
- Agent calls must be typed, audited, authorized, bounded and evaluated.
- AI components should be modular but avoid unnecessary microservices.
- Do not fabricate completed milestones. Every gate requires command, result, commit and date in STATUS.
