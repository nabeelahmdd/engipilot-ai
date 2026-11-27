# CommercePilot AI — Live status

**As of:** 2026-11-27
**Current phase:** ENG-007 — Identity and authentication hardening
**Pull request:** [PR #10](https://github.com/nabeelahmdd/engipilot-ai/pull/10) (draft, open, **not merged**)
**Feature branch:** `feat/ENG-007-email-verification`
**Base:** `main`
**Previous migration:** PR #9 merged on 2026-11-24
**Product:** CommercePilot AI (internal `engipilot_ai` names intentionally retained)

## Delivered identity APIs

Eleven HTTP endpoints are implemented under `/api/v1/auth`:

- `POST /register`
- `POST /resend-verification`
- `POST /verify-email`
- `POST /login`
- `POST /refresh`
- `POST /logout`
- `POST /forgot-password`
- `POST /reset-password`
- `GET /me`
- `PATCH /me`
- `POST /change-password`

The APIs use JWT access tokens, server-side device sessions, single-use hashed
refresh credentials, CSRF proof for browser refresh/logout, Argon2id password
hashing, and encrypted token payloads in the email outbox.

## Acceptance and CI evidence

- **User local manual verification:** reported all 11 API flows working.
- **Python CI at `47cc4045` (2026-11-27):** Ruff lint and format, mypy,
  PostgreSQL smoke, Alembic upgrade and schema alignment, and pytest passed.
- **Automated test suite:** 58 passed, 6 warnings.
- **Web CI at `47cc4045`:** lint, typecheck and build passed.
- **Docker image builds at that check:** queued; recheck latest PR head.
- **Human PR approval / merge:** pending.

## ENG-007 hardening progress

### Implemented — public auth request throttling

Commit `33c1ea4` and follow-up formatting/model-test fixes introduce a
PostgreSQL-backed fixed-window rate limiter for six public endpoints:
register, login, resend verification, verify email, forgot password, and reset
password.

- Default: **12 requests / 60 seconds per source IP per endpoint**.
- Configure with `AUTH_RATE_LIMIT_MAX_REQUESTS` and
  `AUTH_RATE_LIMIT_WINDOW_SECONDS`.
- Counters use a hash of the endpoint and client IP, never a raw IP column.
- Limit response: HTTP `429` with a `Retry-After` header.
- Atomic PostgreSQL upserts make counters shared across API processes.
- Adds the Alembic revision `c79e25a7fd46` and an HTTP regression test.

**Local upgrade requirement:** After pulling the feature branch, run
`uv run --locked alembic upgrade head` against the intended development DB
*before* calling the updated endpoints.

### Remaining before production deployment

1. Test concurrent refresh, logout, and password-change/reset operations.
2. Add rate limiting and bot/DDoS protection at the trusted ingress, and
   confirm the reverse-proxy/IP trust configuration. IP throttling alone does
   not stop distributed credential attacks.
3. Schedule cleanup of old `identity_rate_buckets` records; e.g. a daily
   database task can delete rows older than 24 hours. Do **not** run that
   against an unintended database.
4. Validate email outbox retry/lease handling, and configure a persistent
   worker and a non-local SMTP adapter for production.
5. Recheck the latest CI/Docker jobs and inspect the complete PR diff.
6. Merge PR #10 only after the owner's review and acceptance.

## Upcoming product phases

- **B2 — Catalog:** categories, product variants/SKUs, price and inventory
  models; search/filter/pagination and authorization.
- **B3 — Cart:** authenticated customer cart, quantities, prices and isolation.
- **B4 — Simulated orders:** atomic checkout, stock changes, idempotency.
- **B5 — Domain hardening:** audit, authorization and concurrency checks.
- **A1–A6 — Agentic AI:** LangChain, LangGraph, MCP, RAG, multi-agent, memory,
  evaluations, observability and model routing.

Never merge PR #10 automatically. Start B2 from updated `main` only
after ENG-007 is accepted and merged.
