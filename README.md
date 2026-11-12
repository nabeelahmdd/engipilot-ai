# EngiPilot AI

A **web-first, multi-tenant AI engineering platform** built one complete feature module at a time.

> Status: **Day 1 foundation only**. Organization signup, projects, access control, GitHub App connection, and AI PR reviews are **not implemented yet**.

## Technologies

- Backend: Python 3.12, FastAPI, Pydantic Settings, SQLAlchemy 2, asyncpg, PostgreSQL 17.
- Frontend: React 19, TypeScript, Vite, ESLint.
- Developer tools: uv, pytest, Ruff, mypy, npm, Docker, GitHub Actions.
- Build: Python package using PEP 621 `pyproject.toml`, hatchling, `src/` layout.

## 1. macOS requirements

Install Git, **uv (0.13.7 recommended, to match CI/Docker)**, Node.js 22.12+ (prefer Node 22 LTS), and Docker Desktop (including Compose). On Apple Silicon use the native ARM64 versions where available. VS Code is optional.

Verify prerequisites:

```bash
git --version
uv --version
node --version
npm --version
docker compose version
```

## 2. Setup from ZIP

```bash
unzip engipilot-ai-v0-foundation.zip
cd engipilot-ai-v0-foundation
bash scripts/bootstrap.sh
docker compose up -d postgres
```

Bootstrap copies `.env.example` to ignored `.env`, creates `uv.lock` and `apps/web/package-lock.json` **using your real package registries**, installs dependencies and runs checks. Both lockfiles **must be committed before opening a PR**. The ZIP does not contain fabricated locks because the packaging environment could not access package registries.

## 3. Run locally (two terminals)

```bash
# Terminal 1 - backend, in repository root
make api
# Terminal 2 - frontend, in repository root
make web
```

- Web: http://127.0.0.1:5173
- API health: http://127.0.0.1:8000/api/v1/health
- DB readiness: http://127.0.0.1:8000/api/v1/ready
- Swagger UI: http://127.0.0.1:8000/docs (local/test only)

## 4. Run checks

```bash
make check
uv run --locked pytest -q
uv run --locked mypy src
cd apps/web && npm run build
```

**What is checked?** Python formatting/lint/typechecks, backend tests, frontend lint/typecheck/build. GitHub Actions additionally starts PostgreSQL, performs a database smoke test and builds Docker images.

## 5. Optional full Docker demo

```bash
docker compose -f compose.yaml -f compose.demo.yaml up --build -d
# http://127.0.0.1:8080
docker compose -f compose.yaml -f compose.demo.yaml down
```

Docker demo is for local smoke tests. It is not an approved production deployment or a substitute for TLS, secure identity, managed secrets and infrastructure hardening.

## 6. Git and GitHub Actions

**Git setup:**

```bash
git init -b main
git status --short
git add .
git commit -m "chore(repo): bootstrap Python and React foundations"
```

Only run this **after** `bash scripts/bootstrap.sh` succeeds and both lockfiles exist. `.env`, `.venv`, and `node_modules` are ignored. Create an empty private repository on GitHub, then add its remote and push:

```bash
git remote add origin git@github.com:YOUR_USER/engipilot-ai.git
git push -u origin main
```

After initial bootstrap, do **not** create all feature branches at once. Start each ticket from up-to-date `main`, develop/test, open a PR, merge and delete the branch. Example:

```bash
git switch main && git pull --ff-only origin main
git switch -c feat/ENG-005-org-project-models
# implement real changes and tests
make check
git add src/ tests/ docs/ pyproject.toml uv.lock
git diff --cached --check
git commit -m "feat(organizations): add organization and project schemas"
git push -u origin feat/ENG-005-org-project-models
```

`ENG-005` is a **future task**; do not run the example commit until the code exists. Pull requests trigger CI automatically.

**Documentation:**
- [GitHub Actions, CI/CD walkthrough](docs/GITHUB_ACTIONS_GUIDE.md)
- [File-by-file explanation](docs/FILE_BY_FILE_GUIDE.md)
- [Git workflow](docs/GIT_WORKFLOW.md)
- [V0 architecture](docs/architecture/V0.md)

## 7. Release tags and containers

After approved tests pass and `main` is updated:

```bash
git tag -a v0.0.1 -m "V0 foundation"
git push origin v0.0.1
```

`.github/workflows/release.yml` reruns quality checks and publishes versioned API/web images to GHCR. **No production deployment occurs.** The repository needs Actions and package publishing enabled; see [CI/CD guide](docs/GITHUB_ACTIONS_GUIDE.md).

## 8. Long-term incremental roadmap

- V0: multi-tenant organization/project foundations, approved Git integrations, **web-based AI PR review**.
- V1: codebase-aware RAG and AI chat.
- V2: AI test generation and sandbox validation.
- V3: durable agent workflows/MCP tools.
- V4+: governance, SDKs, more engineering agents and observability.

Private source code must never be sent to unapproved AI providers. The initial skeleton does not make any external AI calls.
