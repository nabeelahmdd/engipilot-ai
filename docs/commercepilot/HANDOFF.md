# Handoff — CommercePilot AI

## Objective
Reuse the existing `nabeelahmdd/engipilot-ai` code and Git history while changing the product to **CommercePilot AI**, a FastAPI commerce backend first and an integrated GenAI/Agentic AI capstone second.

## User's explicit preferences
- Keep architecture: FastAPI, SQLAlchemy, PostgreSQL, auth/session/JWT, Alembic history, CI/CD, Docker, UV + lockfiles, React shell.
- Delete **genuinely unrelated** organization/project modules and their tests, not reusable engineering infrastructure.
- Change all user-facing branding. The internal `engipilot_ai` namespace can remain to avoid extensive rename churn.
- Manually build each next feature, package by package, learning rationale. No prebuilt ZIP setup.

## Current PR
- GitHub: `https://github.com/nabeelahmdd/engipilot-ai/pull/9`
- Branch: `chore/commercepilot-backend-first-reboot`
- PR targets protected `main`, remains unmerged.
- M0 cleanup includes domain-specific deletions, User relationship cleanup, adjusted model tests, displayed brand migration and new guarded database migration.
- Validate actual GitHub diff and CI before claiming complete; the user reviews before merge.

## Resume steps
1. Inspect latest PR #9 and `docs/commercepilot/STATUS.md` (the source of truth).
2. Run checks; do not claim passing unless verified. If migration refuses because legacy data exists, stop and explain backup/export path.
3. Merge only after user verifies tests and migration, then begin catalog design.
4. Keep one feature, one test, one commit, update status each time.

## Later architecture
`FastAPI → domain services → repositories → PostgreSQL`
`LangChain tools/MCP → same domain services`
`LangGraph supervisor → specialist agents → RAG and checkpoints`
`Evals/observability/security across every step`.
