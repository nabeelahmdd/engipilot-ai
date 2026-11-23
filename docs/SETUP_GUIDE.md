# Step-by-step local setup (manual)

## Prerequisites

- macOS terminal with Git, `uv`, Python 3.12 (managed by uv), and an editor.
- No backend/AI packages are preinstalled as part of this reset.
- No ZIP files or generated template application.

## After PR merge and repository rename

```bash
git clone https://github.com/nabeelahmdd/commercepilot-ai.git
cd commercepilot-ai
uv python install 3.12
uv sync
uv run python --version
uv run python -c "import commercepilot_ai; print(commercepilot_ai.__version__)"
```

`uv sync` creates `.venv` and `uv.lock` for the declared project. Commit `uv.lock` in the follow-up PR; do **not** commit `.venv`. If repository rename has not happened, clone with the `engipilot-ai` URL.

## Learn the files

- `pyproject.toml`: project identity, dependency specification and build configuration.
- `.python-version`: selected interpreter major/minor.
- `uv.lock`: resolved dependency graph (generated locally; intentionally absent in reset commit).
- `src/commercepilot_ai/__init__.py`: importable package root.
- `docs/STATUS.md`: live phase ledger and evidence.

## Next B1 step, do not run until B0 is verified

```bash
uv add fastapi "uvicorn[standard]" pydantic-settings
uv add --dev pytest httpx ruff mypy
```

After installing, create `core/config.py`, `main.py` and the health endpoint manually, one file at a time, each with a test.

## Git practice

```bash
git switch main
git pull --ff-only
git switch -c feat/COM-001-fastapi-foundation
# Make one tested, documented change
git status --short
git add <specific-paths>
git commit -m "feat(api): add tested health endpoint"
git push -u origin feat/COM-001-fastapi-foundation
```

Create PR for the verified step. Update status/decision docs before closing a phase.
