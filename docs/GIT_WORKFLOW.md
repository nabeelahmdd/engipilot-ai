# Professional Git workflow — EngiPilot AI

## The rule

**Each commit must represent work you actually completed and tested.** Do not create fake branches/commits simply to make the GitHub graph look busy. We start with one honest scaffold commit, then one branch per engineering task. Protected `main` is kept stable.

## First repository initialization

Install dependencies and generate both committed lockfiles before the first commit:

```bash
bash scripts/bootstrap.sh
ls -lh uv.lock apps/web/package-lock.json
```

Initialize Git inside the extracted directory:

```bash
git config --get user.name
git config --get user.email
# configure your real identity if those print nothing:
# git config --global user.name "Your Name"
# git config --global user.email "your-email@example.com"

git init -b main
git status --short
git check-ignore -v .env .venv/ apps/web/node_modules/
git add .
git diff --cached --check
git diff --cached --stat
git commit -m "chore(repo): bootstrap Python React and CI foundation"
```

Before committing, confirm `.env` is absent from `git diff --cached --name-only` and both `uv.lock` / `package-lock.json` are present.

## GitHub remote

Create a **private empty** repo named `engipilot-ai` on GitHub; don't initialize README/gitignore/license in GitHub. Then:

```bash
git remote add origin git@github.com:YOUR_USERNAME/engipilot-ai.git
git push -u origin main
```

If SSH isn't configured, use the authenticated HTTPS remote or `gh auth login` / `gh repo create` instead. Never put a token into the remote URL.

## Feature branches, one at a time

| Ticket | Branch | Deliverable |
|---|---|---|
| ENG-005 | `feat/ENG-005-org-project-models` | Tenant organization/project models, Alembic migrations and tests |
| ENG-006 | `feat/ENG-006-identity-and-rbac` | Identity integration, role permissions and tests |
| ENG-007 | `feat/ENG-007-github-integration` | GitHub App installation/permission-aware repository discovery |
| ENG-008 | `feat/ENG-008-ai-review` | PR review workflow, structured findings, AI evaluations |
| ENG-009 | `feat/ENG-009-review-web-ui` | PR selection and validated findings display |

For each ticket:

```bash
git switch main
git pull --ff-only origin main
git switch -c feat/ENG-005-org-project-models
# write real implementation and tests
make check
git status
git diff --check
git add src/ tests/ docs/ pyproject.toml uv.lock
git diff --cached --stat
git commit -m "feat(organizations): add tenant project models and migrations"
git push -u origin feat/ENG-005-org-project-models
```

**This is a future example;** don't run the `ENG-005` commit before actually writing those models. Create a GitHub PR from feature branch into `main`, read the Checks tab, review the diff, merge after checks pass. Then:

```bash
git switch main
git pull --ff-only origin main
git branch -d feat/ENG-005-org-project-models
```

## Ruleset and code review

Enable a repository ruleset protecting `main` (GitHub → Settings → Rules → Rulesets). Require PRs and passing checks, restrict force pushes and tag creation when appropriate. Start with check names seen in first successful Actions run, then update branch protection.

Use descriptive Conventional Commit-style subjects:

- `feat(organizations): add project membership policies`
- `fix(github): handle suspended installations safely`
- `test(review): cover partial PR diff responses`
- `docs(ci): explain release quality gates`
- `refactor(ai): separate provider adapter`

## Version tags

A product milestone like V0 can have multiple software releases. Only tag a passing commit on `main`:

```bash
git switch main
git pull --ff-only origin main
git tag -a v0.0.1 -m "Initial foundation release"
git push origin v0.0.1
```

This tag triggers `.github/workflows/release.yml` which publishes container images to GitHub Container Registry, not a live server.
