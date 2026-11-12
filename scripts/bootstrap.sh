#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

for binary in uv npm git; do
  if ! command -v "$binary" >/dev/null 2>&1; then
    echo "Missing $binary. Install it, then rerun bootstrap." >&2
    exit 1
  fi
done

if [[ ! -f .env ]]; then
  cp .env.example .env
  chmod 600 .env
  echo "Created .env using LOCAL-ONLY example values."
fi

echo "Resolving Python dependencies and writing uv.lock..."
uv lock
uv sync --locked

echo "Resolving frontend dependencies and writing package-lock.json..."
(cd apps/web && npm install)

echo "Running validation..."
bash scripts/check.sh
echo "Bootstrap finished. Commit uv.lock and apps/web/package-lock.json."
echo "To run PostgreSQL: docker compose up -d postgres (Docker Desktop required)."
