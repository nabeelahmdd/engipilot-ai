# CommercePilot AI — Existing architecture map

This repository already has an initial Python/React/backend infrastructure and authentication implementation; **do not reinitialize it**.

| File or directory | Responsibility |
|---|---|
| `pyproject.toml`, `uv.lock`, `.python-version` | Python 3.12 dependencies, reproducibility |
| `src/engipilot_ai/main.py` | FastAPI app factory and middleware |
| `src/engipilot_ai/core/config.py` | Environment and validated settings |
| `src/engipilot_ai/core/database.py` | SQLAlchemy async engine and session lifecycle |
| `src/engipilot_ai/core/db_base.py` | Shared ORM base and abstract fields |
| `src/engipilot_ai/api/health.py` | Health/readiness endpoints |
| `src/engipilot_ai/modules/identity/` | User model, password hashing, JWT, registration, sessions |
| `src/engipilot_ai/models/__init__.py` | Import current ORM models into Alembic/SQLAlchemy metadata |
| `migrations/` | Immutable historical Alembic revisions + guarded legacy retirement |
| `tests/` | Unit and integration regression suite |
| `apps/web/` | Existing React/Vite web shell, currently overview/health only |
| `Dockerfile.api`, `Dockerfile.web`, `compose*.yaml` | API/web containers and PostgreSQL |
| `.github/workflows/` | CI checks and container publishing |
| `scripts/`, `Makefile` | Developer commands and validation |
| `docs/commercepilot/` | Current implementation roadmap and evidence |

### Future CommercePilot modules
Add `modules/catalog`, `modules/cart`, `modules/orders` manually once relevant contracts are defined, tested and reviewed. Later add LangChain tools, LangGraph, MCP, RAG, multi-agent and evaluation modules using the same domain services.

### Naming
The Python package `engipilot_ai` and GitHub repository name remain legacy *technical* identifiers for now. Only application-facing branding is CommercePilot AI.
