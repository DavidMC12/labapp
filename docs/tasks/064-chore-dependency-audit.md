# Task 064: dependency audit and Dependabot

Assignee: Worker 1. Branch: `w1/dependency-audit`. Reviewer: Supervisor.

**Base.** Branch from `main`.

## Goal

The repository is public and the demo is about to be deployed online. Before that, know what the dependencies carry: run the audits of both ecosystems, record the result, fix what is worth fixing, and let a bot keep watching. This is hygiene work with a precise deliverable and no feature.

## Read first

`backend/pyproject.toml` and `backend/uv.lock`, `frontend/package.json` and `frontend/pnpm-lock.yaml`, the root `package.json` / `mise.toml` if they exist, `.github/workflows/*.yml` (the actions and their versions), `docs/DEPLOYMENT.md` (how the project is deployed) and `docs/DEVELOPMENT.md` (the commands). The review records in `docs/reviews/` show the format of a record.

## Scope

You may edit: `.github/dependabot.yml` (new), `docs/reviews/2026-11-08-dependency-audit.md` (new), dependency versions in `backend/pyproject.toml` / `backend/uv.lock` / `frontend/package.json` / `frontend/pnpm-lock.yaml` **only** for the fixes of requirement 3, and a short "Dependencies" paragraph in `docs/DEVELOPMENT.md`. No code changes beyond what an upgrade strictly needs. No new runtime dependency.

## Requirements

1. **Audit the frontend.** From `frontend/`: `pnpm audit --prod` and `pnpm audit` (all dependencies). Record, for each finding: package, installed version, advisory id, severity, whether it is a runtime or a build/dev dependency, whether the vulnerable code path is reachable in this application (read the advisory; say "not reachable" only with a reason), and the fixed version.
2. **Audit the backend.** Without adding a dependency to the project, run `uvx pip-audit` against the locked set (for example `uv export --frozen --no-hashes > /tmp/requirements-audit.txt` and then `uvx pip-audit -r /tmp/requirements-audit.txt`, from `backend/`; keep the temporary file outside the repository). Record the same fields. If `pip-audit` cannot reach its vulnerability service from this machine, say so and use `uvx` with another tool only if one works; do not invent results.
3. **Fix what is worth fixing.** A finding with a fixed version that is a **patch or minor** upgrade of a **runtime** dependency, or any High or Critical finding that is reachable, is upgraded now, in its own commit per package (`build(backend): ...` or `build(frontend): ...`), with the full acceptance commands passing after each. A finding that needs a major upgrade, or is a dev-only tool with no reachable path, is **not** upgraded: it goes into the record with the decision and the reason. Do not upgrade anything else.
4. **The record** `docs/reviews/2026-11-08-dependency-audit.md`: the commands run and their date, one table per ecosystem (the fields of requirement 1), what was upgraded (with the before and after versions), what was left and why, and the numbers (how many findings by severity before and after). English, no secrets, no local paths.
5. **Dependabot.** `.github/dependabot.yml` version 2 with: the `npm` ecosystem for `/frontend` (and the root if it has a `package.json` with dependencies), the `uv` ecosystem for `/backend` (check that the current Dependabot documentation lists `uv`; if the installed information is unclear, use `pip` for `/backend` and say so), and `github-actions` for `/`; a weekly schedule on Monday, `open-pull-requests-limit: 5` per ecosystem, `groups` so that minor and patch updates of an ecosystem arrive as one pull request, and `commit-message` with `prefix: "build"` and `include: scope` so that the bot's commits follow Conventional Commits (the CI checks the subject of every commit). Validate the YAML (`python3 -c "import yaml,sys; yaml.safe_load(open('.github/dependabot.yml'))"` or the equivalent) and explain in the report why each key is there.
6. **The workflows.** List in the record every `uses:` of `.github/workflows/*.yml` with its version tag and say which are pinned to a full commit SHA (none is required now); recommend, in one sentence, what to do about it. Do not change the workflows.
7. **DEVELOPMENT.md.** A short paragraph: how to re-run both audits (the exact commands) and that Dependabot opens the pull requests.

## Acceptance criteria

From `frontend/`: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test:coverage`, `pnpm build` pass; from `backend/`: `uv sync --frozen`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest -q -W error --cov=app --cov-report=term` pass; from the repository root: `node tools/audit/docs-lint.mjs` exits 0. Both lockfiles are consistent after any upgrade (`--frozen-lockfile` and `uv sync --frozen` pass). The supervisor re-runs the audits and the gates.

## Rules for this task

- Commit as you go, in small real steps (about 4 to 8 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- If a command runs more than 3 minutes, interrupt it (esc) and look for the cause.
- If something is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, the counts of findings before and after by severity, what you upgraded and what you left, and any deviation or open question.
