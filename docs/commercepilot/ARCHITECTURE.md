# Architecture — preserved foundation, new CommercePilot domain

## Existing maintained foundation

```text
React web shell ──→ FastAPI app (src/engipilot_ai/main.py)
                           |
          Shared identity/auth and application modules
                           |
           SQLAlchemy 2 async + Alembic + PostgreSQL
                           |
           UV · pytest · Ruff · mypy · Docker · CI
```

The existing `engipilot_ai` package name is a *technical compatibility identifier*, not the displayed product name. No e-commerce CRUD or AI agent should be claimed functional yet.

## Target incremental architecture

```text
React or CLI
     |
 FastAPI routes  ────────────────────────────────────────┐
     |                                                   |
 Domain application services <──────────── AI tool adapters / MCP
     |                     (auth + validation)           ^
 repositories + policies                                |
     |                                             LangGraph
 PostgreSQL                                     supervisor + agents
                                                     /       \
                                               RAG retrieval  memory
                                                     \       /
                                             Evals · traces · security
```

## Keep vs remove

**Keep (actual code):** `core/config.py`, `core/database.py`, `core/db_base.py`, `api/health.py`, `main.py`, `modules/identity/`, `models/`, `migrations/` historical revisions, `apps/web/`, `tests/` general/identity, `scripts/`, Dockerfiles, Compose, `.github/workflows/`, `pyproject.toml`, `uv.lock`.

**Remove as unrelated domain:** `modules/organizations/`, `modules/projects/`, tests that exercise only those models. User model relationships and model registration must be adjusted in same PR. Add an Alembic migration to remove legacy tables only when empty.

**Add incrementally:** `modules/catalog/`, `modules/cart/`, `modules/orders/` and later AI tool, graph, agent, MCP, RAG and evaluator directories. Don't prebuild empty folders.

## Safety
- No direct model-generated SQL, shell, payment or destructive commands.
- Server-computed currency totals and DB transaction boundaries.
- Customer ownership and authorization validated for every path including agent/MCP tools.
- Checkpoint state != long-term memory != knowledge retrieval; use different retention rules.
- No sensitive traces or private data leaking to model provider by default.

## Why the old migration files remain
Alembic revision history is immutable once it may be deployed. We add a **new guarded revision** to transition from the old tables; deleting old revision files breaks clean installation and upgrades.
