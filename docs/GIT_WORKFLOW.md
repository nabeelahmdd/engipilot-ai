# CommercePilot AI — Git and PR workflow

Keep the existing protected `main` branch. Each change is a real, tested vertical slice with one pull request. **Never force-push or delete old Git history to rename the product.**

## Normal workflow

```bash
git switch main
git pull --ff-only origin main
git switch -c feat/COM-001-catalog-model
# Make one verified change and tests
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy src
uv run --locked pytest -q
git status --short
git diff --check
git add src/ tests/ docs/ migrations/ pyproject.toml uv.lock
git diff --cached --stat
git commit -m "feat(catalog): add validated product model"
git push -u origin feat/COM-001-catalog-model
```

Create a pull request and review its Files changed and Checks tabs. Merge only after passing CI and human review. Don't blindly stage unrelated local files.

## CommercePilot roadmap branch examples

- `feat/COM-001-catalog-model`: product/category model, migration and tests
- `feat/COM-002-catalog-api`: routes, schemas, validation
- `feat/COM-003-cart`: ownership and cart transactional changes
- `feat/COM-004-orders`: simulated checkout/order state machine
- `feat/COM-101-langchain-tools`: authorized AI tool adapters
- `feat/COM-102-langgraph-agent`: workflow state and approval
- `feat/COM-103-mcp`: MCP client/server against same services

### Source of truth
Update `docs/commercepilot/STATUS.md` and any decision document along with each implementation PR. Don't claim a feature completed until tests pass.

### Project naming note
The repository URL is presently `nabeelahmdd/engipilot-ai` and the import namespace remains `engipilot_ai` for compatibility; **CommercePilot AI** is the application/product name. Rename technical identifiers only in a coordinated tested PR.

### Releases
Tag only a green `main` commit. Release workflow publishes versioned container images; it does **not** deploy a production application. Keep `.env`, secrets and private datasets out of Git.
