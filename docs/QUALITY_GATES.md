# Quality gates and review checklist

## B0 repository pivot
- [ ] Proposed PR replaces EngiPilot identity everywhere in *new* files.
- [ ] Old React, old code-review/identity/org/project and old migrations are absent from new tree.
- [ ] No secrets committed; `.env` ignored.
- [ ] `pyproject.toml` builds the `commercepilot_ai` source package.
- [ ] Existing Git history preserved (normal PR, no branch force-push).
- [ ] Review deletions and approve merge; manual rename handled separately.

## Each backend phase
- [ ] Unit tests for services/validation.
- [ ] Integration tests where DB or network involved, hermetic when possible.
- [ ] Negative tests: invalid inputs, duplicate actions, permission/ownership checks.
- [ ] Alembic migration tested, transactions consistent.
- [ ] Ruff and pytest pass from clean environment.
- [ ] API contract and failure responses documented.
- [ ] No real payment/return external side effects.

## Each AI phase
- [ ] Typed tool inputs/outputs and least-privilege actor context.
- [ ] LLM cannot override deterministic domain validation.
- [ ] Tool choice, trace trajectories and failure paths measured against a curated dataset.
- [ ] RAG answers grounded to versioned sources; unsupported claims handled.
- [ ] HITL confirmation captured before sensitive operations.
- [ ] Prompt injection and cross-user access tested.
- [ ] Tokens, costs, latency, error rates recorded; sensitive data redacted.
- [ ] Checkpoint crash/restart and idempotent retry tests.
- [ ] Multi-agent added only if it improves measurable quality over single agent.

## Definition of done
A checked item includes the **command, test result, commit/PR reference and date** in `docs/STATUS.md`. Never mark planned examples as implemented.
