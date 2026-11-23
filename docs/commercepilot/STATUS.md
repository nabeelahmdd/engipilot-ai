# CommercePilot AI — Live status

**Phase:** M0 migration/branding  
**PR:** #9 — proposed, not merged  
**GitHub repository:** `nabeelahmdd/engipilot-ai`; intentional technical identifier  
**Displayed product:** CommercePilot AI  
**Backend:** existing FastAPI/auth/PostgreSQL foundation; no commerce APIs yet  
**AI:** not implemented

## Migration change plan
- Preserve all required architecture, auth code, tests, CI, Docker, Compose and both lockfiles.
- Remove only old organization/project modules and related tests plus obsolete planning docs.
- Update user-facing README, FastAPI app/health labels, React page, HTML and matching tests.
- Change identity User model to remove obsolete relationships; retain user registration/login/session/token machinery.
- Add guarded Alembic table-removal revision. **It refuses if any legacy table has data.**
- Keep internal package name, database identifiers, Docker names and GitHub URL unchanged for compatibility.

## Evidence ledger
| Gate | State |
|---|---|
| Main branch audited | Done via GitHub file tree and content inspection |
| PR scoped to related code rather than architecture wipe | In progress |
| PR diff verified for expected removals | Pending |
| Static syntax/quality inspection | Pending |
| CI success | Pending |
| Migration on fresh database | Not run |
| Migration with existing legacy data | Not run |
| GitHub rename | Not planned now |
| Human review and merge | Pending |
| Commerce catalog/cart/orders | Not started |

## Next exact task
1. Review PR #9 changed files; do not merge until CI and DB migration tests are green.
2. Run `uv sync --locked`, `uv run --locked ruff check .`, `uv run --locked ruff format --check .`, `uv run --locked mypy src`, `uv run --locked pytest -q`.
3. Run `uv run --locked alembic upgrade head` in test DB; verify empty table guard, and separately verify that legacy table rows block migration (do not test destructively on personal DB).
4. Record evidence and merge only when approved.
5. Start B2 — catalog schema design, one file and test at a time.
