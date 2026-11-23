# CommercePilot AI — GitHub Actions CI/CD guide

## Existing workflows retained

- `.github/workflows/ci.yml`: Python 3.12/UV reproducibility, Ruff, mypy, PostgreSQL service and Alembic verification, pytest; React lint/build; Docker image build.
- `.github/workflows/release.yml`: checks tagged releases, publishes versioned container images to GHCR. This is not a production deployment.

## How to inspect PR #9

Open GitHub → Pull requests → PR #9 → Files changed. Confirm core/auth/CI/Docker/React are retained, and that organization/project removals are the only domain deletions. Open **Checks** for backend/frontend/container results.

## Local checks

```bash
uv sync --locked
docker compose up -d postgres
uv run --locked python scripts/check_database.py
uv run --locked alembic upgrade head
uv run --locked alembic check
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy src
uv run --locked pytest -q
(cd apps/web && npm ci && npm run lint && npm run build)
```

The new migration refuses to delete populated old tenant tables. If it fails, preserve DB volumes, back up data and plan migration. Do not drop data just to get a green build.

## Notes

- `uv.lock` and `apps/web/package-lock.json` stay committed. CI uses locked installation.
- The existing GitHub repo name, internal package namespace and image tags may still contain legacy identifiers during transition. User-facing product is CommercePilot AI.
- Never commit AI API keys, authentication secrets or customer data.
- GitHub Actions logs are evidence: don't mark a check green without observing the actual run.
