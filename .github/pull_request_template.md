## CommercePilot AI — Change summary
What changed and why?

## Scope / issue
Ticket: COM-

## Evidence / checks
- [ ] `uv run --locked pytest -q`
- [ ] `uv run --locked ruff check .`
- [ ] `uv run --locked ruff format --check .`
- [ ] `uv run --locked mypy src`
- [ ] `uv run --locked alembic check` (if schema changed)
- [ ] `npm run build` in `apps/web` (if applicable)

## Security and migration
- [ ] No secrets or real customer data
- [ ] Sensitive operations and ownership checks covered
- [ ] Database migration is reversible/guarded as documented
- [ ] Updated `docs/commercepilot/STATUS.md`

## Test evidence
Commands, CI links, sanitized logs or screenshots:
