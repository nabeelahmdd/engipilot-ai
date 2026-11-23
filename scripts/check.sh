#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test -s uv.lock || { echo "Missing uv.lock: run bash scripts/bootstrap.sh" >&2; exit 1; }
test -s apps/web/package-lock.json || { echo "Missing apps/web/package-lock.json: run bash scripts/bootstrap.sh" >&2; exit 1; }
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy src
uv run --locked pytest -q
(cd apps/web && npm ci && npm run lint && npm run build)
