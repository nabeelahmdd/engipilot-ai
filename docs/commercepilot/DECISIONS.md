# Decisions — CommercePilot AI

| ID | Decision | Explanation |
|---|---|---|
| CP-001 | Retain existing core/identity architecture | We already have usable authentication, DB, tests, Docker, CI, frontend setup |
| CP-002 | Retire org/project business modules | These are engineering tenant/project concepts, not required for the single-store commerce capstone |
| CP-003 | Preserve historical migrations | Never rewrite Alembic revisions; guard table removal if prior data exists |
| CP-004 | Display CommercePilot AI everywhere user-facing | README, API metadata, health response, React page, HTML |
| CP-005 | Keep `engipilot_ai` import package and `engipilot-ai` repo temporarily | Prevent unnecessary lockfile/import/CI/Docker/migration churn |
| CP-006 | Backend first, AI after | Tools call real authorized services instead of bypassing domain logic |
| CP-007 | No real payments or refunds | Only simulated checkout and returns |
| CP-008 | Manual, phase-wise UV development | User learns each directory, package, test and trade-off |
| CP-009 | Preserve React shell for later | Not on early critical path but reusable |
| CP-010 | Model output cannot override domain authorization | Shared service boundary for REST, MCP, agents |

## Deferred
- End-to-end technical rename (package, GitHub URL, DB, Docker image names)
- Provider selection, vector DB, trace platform, production hosting
- Redis/queue background processing beyond measurable need
