# CommercePilot AI

**Status:** repository pivot in progress. This branch resets the previous EngiPilot AI code-review app; it does **not** claim a working e-commerce backend or AI agent yet.

CommercePilot AI is a **backend-first e-commerce and agentic AI engineering project**. We will manually implement a real e-commerce backend first, then add LangChain, LangGraph, multi-agent orchestration, MCP, RAG, evaluation, observability and production controls.

## Why the pivot?

We are repurposing the existing Git repository, keeping its commit history, but removing the old code-review, organization/project, authentication, React and deployment scaffold from the proposed branch. The previous application remains recoverable in Git history. Nothing in this PR merges automatically.

## Locked goals

1. Learn by building every layer manually, step by step, using `uv` and Python 3.12.
2. Start with FastAPI + Pydantic + PostgreSQL + SQLAlchemy/Alembic, with verified CRUD, business rules and tests.
3. Support catalog search, customers, carts and **simulated** orders/returns. No real money movement.
4. Introduce AI via domain tools so agents **never** bypass application authorization or business logic.
5. Demonstrate LangChain, LangGraph, MCP, RAG, memory, HITL, multi-agent routing, evaluations, tracing, reliability and security in one coherent demo.
6. Record each completed step, failing case, architecture decision and exact next task.

## Planned stack (not installed yet)

- **Backend:** Python 3.12, FastAPI, Pydantic, PostgreSQL, SQLAlchemy 2, Alembic
- **Dependency management:** uv, `pyproject.toml`, committed `uv.lock` once locally generated
- **Testing:** pytest, Ruff, mypy, httpx
- **AI:** LangChain, LangGraph, MCP Python SDK, vector retrieval, evals and tracing
- **Optional later:** Redis/background jobs, Docker, React UI
- **External data:** DummyJSON only as an optional *seed* or fixture. Our backend database owns persistent products/carts/orders.

## Roadmap at a glance

| Phase | Outcome |
|---|---|
| B0 — Repository reset | New name, docs, minimal Python package (this PR) |
| B1 — API foundation | FastAPI app factory, health and config, tests |
| B2 — Data foundation | PostgreSQL, SQLAlchemy, Alembic, repository/service boundaries |
| B3 — Catalog | Products/categories/search/filter/pagination |
| B4 — Cart | Customer-scoped persistent cart, deterministic pricing |
| B5 — Orders | Simulated checkout/order state transitions, inventory guardrails |
| B6 — Authorization | Identity and ownership checks, auditability |
| A1 — LangChain | LLM configuration, structured outputs, validated tools |
| A2 — LangGraph | State, graph orchestration, checkpoints and HITL |
| A3 — MCP | Discover and call the *same* backend operations via MCP |
| A4 — RAG | Ingestion, vector/hybrid retrieval, reranking, citations |
| A5 — Multi-agent | Router/supervisor, specialized agents, controlled handoffs |
| A6 — Production AI | Evals, trace observability, reliability, security, cost control |
| F — Capstone | End-to-end acceptance scenarios, documentation and reproducibility |

See [MASTER_PLAN](docs/MASTER_PLAN.md), [ARCHITECTURE](docs/ARCHITECTURE.md) and [STATUS](docs/STATUS.md).

## Current repository structure

```text
src/commercepilot_ai/    # New Python package, intentionally minimal
docs/                    # Source of truth for roadmap and decisions
pyproject.toml            # UV project metadata; dependencies deliberately staged
.env.example              # Non-secret configuration examples
```

## Local first step (after reviewing and merging this PR)

```bash
git clone https://github.com/nabeelahmdd/commercepilot-ai.git
cd commercepilot-ai
uv sync
uv run python -c "import commercepilot_ai; print('package import OK')"
```

**Important:** The GitHub repository URL changes to `commercepilot-ai` **only after** the owner manually renames it under GitHub Settings → General → Repository name. Until then use the existing `engipilot-ai` URL. GitHub repository renaming cannot be performed by this PR.

No API endpoint is implemented in this repository-reset PR.

## Our development rule

**One concept → one implementation → one test → one green check → one commit → update `docs/STATUS.md`.** No AI dependencies until the backend feature gates pass.

See [SETUP_GUIDE](docs/SETUP_GUIDE.md) and [HANDOFF](docs/HANDOFF.md).
