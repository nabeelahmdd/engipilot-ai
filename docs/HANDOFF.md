# Resume instructions — CommercePilot AI

## Identity
This is the former `nabeelahmdd/engipilot-ai` project, being repurposed into **CommercePilot AI**, a backend-first e-commerce plus agentic AI capstone. We keep Git history. The GitHub repository must be renamed manually after merging the migration PR.

## User working style
- Manual, one-file/one-command-at-a-time guidance; explain each design decision.
- Use `uv`, Python 3.12, `src/` layout.
- Backend first (FastAPI, PostgreSQL, products, carts, simulated orders); AI modules afterward.
- Do not generate ZIPs or secretly create the whole app.
- Keep everything one repo, modular boundaries, observable/testable feature gates.

## State at this handoff
- B0 reset branch: `chore/commercepilot-backend-first-reboot`.
- No active commerce backend yet; new package is minimal.
- Original EngiPilot content is available in `main` until merge and in commit history thereafter.
- Treat `docs/STATUS.md` as the live source of truth; this summary may be stale.

## Every future session
1. Read latest `docs/STATUS.md`, `docs/MASTER_PLAN.md`, and current GitHub branch/PR status.
2. Confirm the exact phase and code/files present (not remembered guesses).
3. Explain *one* implementation step, have the user run it, examine output/tests.
4. Mark a task done only with passing evidence; commit and update status/decisions.
5. Keep clear separation between confirmed changes and planned work.

## First lesson after migration
- Interpret `pyproject.toml`, `.python-version`, `uv.lock`, `src/commercepilot_ai/`.
- Run `uv sync` locally and verify import.
- Install FastAPI/uvicorn/settings in B1 with `uv add`.
- Create the app factory and a health route **manually** with a unit test.
