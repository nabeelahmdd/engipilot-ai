# CommercePilot AI

**Backend-first E-commerce & Agentic AI Engineering Capstone**

CommercePilot AI is a modular Python/FastAPI e-commerce application that will progressively add LangChain, LangGraph, MCP, RAG, multi-agent orchestration, evaluation, observability and production safety.

> **Status:** Existing FastAPI, PostgreSQL, authentication, React and CI foundations are present. The catalog, cart, orders and AI features are **planned, not implemented**.

## Our decision

Reuse the existing architecture rather than rebuilding it. The previous engineering-project-specific organization/project modules are retired in this migration; identity/authentication, SQLAlchemy, Alembic history, API, tests, React, Docker, CI and UV dependency management remain.

**Naming:** The product and user-facing branding is **CommercePilot AI**. For compatibility, the existing GitHub repo is still `nabeelahmdd/engipilot-ai` and the Python import package is still `engipilot_ai`. Technical identifiers (Python imports, JWT audience/issuer defaults, Docker names, database names and package lockfile) are intentionally retained until a coordinated rename is justified. Do not confuse them with product branding.

## Goals

1. Build a real backend: customer identity, catalog, persistent cart, inventory and **simulated** orders.
2. Provide clean, authorized domain services consumed by REST endpoints and future AI tools.
3. Implement a complete production-oriented agentic workflow with LangChain, LangGraph, MCP, RAG, memory, multi-agent and HITL.
4. Evaluate tool choice, retrieval, reasoning trajectories, latency, cost and resilience.
5. Build everything incrementally, **manually**, with `uv` and evidence-based tests.

No live payment processing, real refunds or fulfillment actions are in scope.

## Existing technology

Python 3.12, uv + locked dependencies, FastAPI, async SQLAlchemy, PostgreSQL 17, Alembic, Pydantic Settings, JWT/password/session auth utilities, React + Vite, Docker/Compose, pytest, Ruff, mypy, GitHub Actions.

## Roadmap

| Phase | Capability |
|---|---|
| M0 | Migrate branding and retire unrelated engineering domains with a guarded DB migration |
| B1 | Verify baseline, auth, tests, PostgreSQL migration and CI |
| B2 | Products, categories, pricing, inventory and search APIs |
| B3 | Customer-owned carts and transactions |
| B4 | Simulated order creation and status |
| B5 | Authorization, audits and concurrency tests |
| A1 | LangChain LLM + typed tool adapters |
| A2 | LangGraph workflow, checkpoints, HITL |
| A3 | MCP client/server |
| A4 | RAG/advanced retrieval and cited policies |
| A5 | Multi-agent supervisor, specialist handoffs |
| A6 | Memory, evals, observability, model routing, production controls |
| F | End-to-end capstone and reproducible demonstration |

Read [roadmap](docs/commercepilot/MASTER_PLAN.md), [architecture](docs/commercepilot/ARCHITECTURE.md), [status](docs/commercepilot/STATUS.md), and [handoff](docs/commercepilot/HANDOFF.md).

## Existing local setup

```bash
git clone https://github.com/nabeelahmdd/engipilot-ai.git
cd engipilot-ai
uv sync --locked
docker compose up -d postgres
uv run --locked alembic upgrade head
uv run --locked pytest -q
uv run --locked ruff check .
```

**Migration warning:** The new Alembic revision intentionally refuses to drop populated legacy organization/project tables. If it blocks, **do not clear database volumes**; inspect and back up data before deciding on the safe conversion. Existing PostgreSQL names are unchanged for compatibility.

API: `http://127.0.0.1:8000`; Web: `http://127.0.0.1:5173` using `make api` and `make web` after setup.

**Learning workflow:** one module → one explained change → tests → PR → update `docs/commercepilot/STATUS.md`. No ZIP scaffolds, no premature mass package installation.
