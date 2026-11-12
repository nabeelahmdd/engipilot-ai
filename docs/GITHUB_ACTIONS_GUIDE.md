# GitHub Actions: learning CI/CD with EngiPilot AI

## 1. Concepts

- **Workflow**: a YAML file in `.github/workflows/`.
- **Event**: what causes it to run, e.g. `push`, `pull_request`, or tag creation.
- **Job**: a collection of steps on a runner; different jobs can run in parallel.
- **Runner**: a temporary GitHub-hosted machine (`ubuntu-latest`).
- **Step**: a shell command (`run:`) or a reusable action (`uses:`).
- **Service container**: PostgreSQL started for integration checks in the backend job.
- **Permissions**: minimum permissions for the automatic `GITHUB_TOKEN`.
- **Artifact**: a build output, such as a container image or test report.

## 2. CI: `.github/workflows/ci.yml`

Triggered for pull requests and pushes to `main`, and manually via **Actions → CI → Run workflow**.

`backend` installs Python 3.12 with uv, syncs the committed `uv.lock`, runs Ruff, mypy and pytest, and checks a real PostgreSQL connection. It never needs a live AI-provider token.

`frontend` installs Node 22, runs `npm ci` from committed `apps/web/package-lock.json`, lints the frontend, typechecks TypeScript, and builds Vite assets.

`images` waits for both backend and frontend and **builds both Docker images without pushing them**.

Why use `uv sync --locked` and `npm ci`? CI should fail if the committed dependency lock is absent/out of date instead of silently resolving new dependencies.

## 3. CD: `.github/workflows/release.yml`

CD only runs when you push a tag beginning `v`, for example `v0.0.1`.

1. Reuses the CI workflow (`workflow_call`), including the Docker build checks.
2. Gets `packages: write` only in the publish job.
3. Authenticates to GitHub Container Registry with the workflow-provided `GITHUB_TOKEN`.
4. Builds and publishes two images tagged with the Git tag:
   - `ghcr.io/OWNER/engipilot-ai-api:v0.0.1`
   - `ghcr.io/OWNER/engipilot-ai-web:v0.0.1`

This is **continuous delivery** of image artifacts, NOT an automatic production deploy. Cloud credentials, domain, TLS, secret-manager and approval environment are intentionally not configured.

## 4. How to examine a run

Open GitHub → repository → **Actions** → **CI** → latest run. Open `backend`, `frontend`, or `images` to inspect each step's terminal log and failure. Open a pull request → **Checks** to see the required statuses.

On a new private repository, enable Actions if prompted. Under Settings → Branches/Rulesets, protect `main`; require the backend, frontend and images checks (use actual check names from the first run). Merge via PR instead of direct push.

For the first release, after the CI passes on `main`:

```bash
git switch main
git pull --ff-only origin main
git tag -a v0.0.1 -m "V0 foundation release"
git push origin v0.0.1
```

Then open Actions → **CD - Publish Images** and inspect the publish job; verify package visibility and repository access in the Packages settings if necessary.

## 5. Branches and PRs

1. `git switch main && git pull --ff-only`
2. `git switch -c chore/ENG-001-foundation`
3. Make a single logical change, run `make check`, `git diff --check`, and commit.
4. `git push -u origin chore/ENG-001-foundation`
5. Create PR, inspect CI, review, merge through GitHub.

The repository skeleton in this archive has no fabricated git history. You create your own real commits.

## 6. Important safety and debugging

- `.env` is local only and should never be pushed. Never expose LLM/provider credentials in test logs.
- The sample database passwords are only for local dev/ephemeral CI.
- If `uv sync --locked` fails: run `uv lock` locally, test, then commit `uv.lock`.
- If `npm ci` fails: run `npm install` locally, test, then commit `package-lock.json`.
- `docker build` on CI is not the same as starting deployed containers.
- Tag-based release should be restricted to authorized maintainers using repository rulesets.
- For stronger supply-chain security, pin action references to reviewed full commit SHAs and enable Dependabot updates; the starter uses readable major-version tags to make learning easier.
