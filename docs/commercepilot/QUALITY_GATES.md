# CommercePilot AI — Quality Gates

## M0 migration acceptance
- [ ] Existing core, auth, app, tests, CI, Docker, React, UV lock remain intact.
- [ ] Only unneeded organization/project module files and obsolete docs/tests are removed.
- [ ] No stale imports of deleted domains in active Python code.
- [ ] API and UI show CommercePilot AI, and matching tests assert new metadata.
- [ ] Alembic revision history remains intact with additive guarded cleanup migration.
- [ ] Empty-DB upgrade and schema alignment check pass.
- [ ] Populated legacy tenant tables *block* migration without data loss.
- [ ] Ruff lint/format, mypy, pytest and frontend build pass.
- [ ] PR human-reviewed before merge.

## Backend feature gates
- [ ] Typed request/response schemas; deterministic validation
- [ ] Authenticated object ownership and negative tests
- [ ] DB transactions, idempotency and concurrency where needed
- [ ] Error response contracts and regression tests
- [ ] STATUS evidence updated

## AI feature gates
- [ ] Typed tool schemas and authorized actor context
- [ ] MCP and agent cannot bypass REST service authorization
- [ ] RAG relevance, freshness, provenance and citation tests
- [ ] HITL accept/reject and interrupted checkpoint recovery
- [ ] Trace-level agent trajectory evaluation
- [ ] Prompt injection, PII redaction and least privilege tests
- [ ] Model routing, cost, latency, retries and fallback measured
