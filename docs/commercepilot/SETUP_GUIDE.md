# CommercePilot AI — Manual existing-repository setup

The existing repository is **not** a fresh Python project. Do not run `uv init`, do not delete lockfiles and do not recreate the architecture.

```bash
git clone https://github.com/nabeelahmdd/engipilot-ai.git
cd engipilot-ai
uv sync --locked
docker compose up -d postgres
uv run --locked alembic upgrade head
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked mypy src
```

`alembic upgrade head` runs the CommercePilot migration, which refuses to drop old organization/project tables if any contain data. Do not delete database volumes to bypass this check. Make a test DB or plan a data migration first.

Existing scripts: `make api`, `make web`, `make check`. Use exact working directory and installed dependencies.

### Next manual lesson
1. Inspect existing `src/engipilot_ai/modules/identity`, `core/database.py`, `core/db_base.py` and API.
2. Design `modules/catalog` with one model, schema, repository, service and test at a time.
3. Introduce packages only via `uv add`; commit `uv.lock` updates.
4. Pass regression suite, make feature PR and update STATUS.

### Technical names
Repository, import namespace and database names remain EngiPilot-derived for now intentionally, while visible product is CommercePilot AI. Rename these together in a separate tested change only if necessary.
