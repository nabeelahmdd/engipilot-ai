# CommercePilot AI — Live status

**Version:** 0.1.0  
**Phase:** B0 — Repository pivot  
**State:** Draft PR #9 opened; not merged  
**Working product:** None yet. Old EngiPilot code is proposed for removal, not deleted from Git history.

## Evidence / progress

| Check | Status | Evidence |
|---|---|---|
| Read original repository and open PRs | Done | `main` reviewed before reset |
| Branch containing new identity/docs | Done | `chore/commercepilot-backend-first-reboot` |
| PR opened | Done | https://github.com/nabeelahmdd/engipilot-ai/pull/9 |
| PR review and merge | Pending (human decision) |
| GitHub repository rename | Pending (requires Settings → General) |
| Local `uv sync` and package import | Not run |
| Backend API / database | Not started |
| LangChain, LangGraph, MCP, RAG | Not started |
| Tests | Not run; no executable feature exists yet |

## Important migration notes

- Five existing Dependabot PRs target the old React app and become obsolete after migration. Review/close **after** the new baseline merges, not as part of this source reset.
- The existing `uv.lock` is intentionally removed because it pins EngiPilot dependencies. Regenerate by running `uv sync` locally and commit it with the next setup step.
- The old app's auth, organization/project models, migrations, web files, Docker and CI are not reusable unchanged. No deployment should occur from this reset PR.

## Next exact task

1. Review the reset PR and confirm intended removals.
2. Merge manually if approved; rename GitHub repo to `commercepilot-ai` in Settings (not possible via PR).
3. Clone/refresh locally; run `uv sync`, `uv run python -c "import commercepilot_ai"`; commit new `uv.lock`.
4. Start B1.1: introduce FastAPI/uvicorn/settings via `uv add`, build and test first health endpoint.
5. Update this file after each verified step.
