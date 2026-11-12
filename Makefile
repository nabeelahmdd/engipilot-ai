.PHONY: bootstrap api web db-up db-down lint test check images

bootstrap:
	bash scripts/bootstrap.sh

api:
	uv run --locked uvicorn engipilot_ai.main:app --reload --host 127.0.0.1 --port 8000

web:
	cd apps/web && npm run dev

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

lint:
	uv run --locked ruff check .
	uv run --locked ruff format --check .
	uv run --locked mypy src
	cd apps/web && npm run lint

test:
	uv run --locked pytest -q

check:
	bash scripts/check.sh

images:
	docker build -f Dockerfile.api -t engipilot-api:local .
	docker build -f Dockerfile.web -t engipilot-web:local .
