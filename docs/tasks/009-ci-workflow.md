# Task 009: continuous integration workflow

Assignee: Worker 2. Branch: `w2/ci`. Reviewer: Supervisor.

## Goal

Run the backend and frontend checks automatically on every pull request and on every push to `main`, in a clean environment, with the same commands the project documents. Before this task only the commit-message workflow existed.

## Read first

- `mise.toml`: the pinned Node, pnpm and uv versions. It is the single source of truth for tool versions.
- `backend/README.md` and `frontend/README.md`: the commands that must pass.
- `.github/workflows/commit-standards.yml`: the style already used (least-privilege permissions, concurrency, timeouts, untrusted values passed through `env`). Do not change that file.
- `backend/pyproject.toml`: the supported Python version.

## Scope

You may create only `.github/workflows/ci.yml`. Do not change any other file.

## Requirements

1. **Triggers and limits.** The workflow is named `ci`. It runs on `pull_request` and on `push` to `main`. `permissions` is `contents: read` at the top. A `concurrency` group per workflow and ref cancels runs in progress. Every job has `timeout-minutes: 15`.
2. **Pinned actions.** Every action, including `actions/checkout`, is pinned by its full 40-character commit SHA, with the tag it corresponds to in a trailing comment, for example `uses: actions/checkout@<sha> # v4.2.2`. Look the SHAs up with `git ls-remote --tags https://github.com/<owner>/<repo>` (for an annotated tag use the SHA of the dereferenced `^{}` entry) and pick a release that is at least two weeks old. Do not guess or copy SHAs from memory.
3. **Tools.** Install Node, pnpm and uv at the versions of `mise.toml` with `jdx/mise-action`, so the versions are written in one place only. Python for the backend comes from uv: add a `uv python install 3.14` step before `uv sync`.
4. **Job `backend`** (`working-directory: backend`): `uv sync --frozen`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest -q -W error`.
5. **Job `frontend`** (`working-directory: frontend`): `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`, in this order (typecheck before build is how a clean checkout behaves).
6. **Shape.** The two jobs are independent and run in parallel. Their job ids are exactly `backend` and `frontend`, so they can later be made required checks. No secrets, no deployment, no artifacts.
7. **Local validation.** The YAML must parse; run every command of both jobs in the working directory with the real exit status of each, and check that the SHAs resolve.

## Acceptance criteria

`.github/workflows/ci.yml` is the only file changed, the YAML parses, every action is pinned by a verified full SHA with its tag in a comment, and each command of both jobs passes locally. The first run on GitHub must be green.

## Rules for this task

Small real commits in Conventional Commits, in English; no `Co-Authored-By` or tool-attribution line; no push, no merge, nothing on `main`; relative paths only; write the question in the report instead of guessing; report the branch, the commit range, the exact commands with their results and any deviation.
