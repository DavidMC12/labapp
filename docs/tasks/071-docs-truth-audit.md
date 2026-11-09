# Task 071: a truth audit of the deployment, development and architecture documents

Assignee: Worker 2. Branch: `w2/docs-truth-audit`. Reviewer: Supervisor.

**Base.** Branch from `main`.

## Goal

The owner is about to follow `docs/DEPLOYMENT.md` for the first time, on a service that has never been used with this repository. Every command, file name, variable, port and claim in the deployment, development and architecture documents must be true **today**. The documentation linter checks links and ids; it does not check that `API_URL` is the name the code reads, that `mise run dev` exists, or that a described step still happens. Read those documents like a person who follows them with no other help, check each statement against the repository, and fix what is wrong.

## Read first

`docs/DEPLOYMENT.md`, `docs/DEVELOPMENT.md`, `docs/ARCHITECTURE.md`, `.env.example` (root and `backend/`, `frontend/` if they exist), `vercel.json`, `mise.toml`, `scripts/` (every script), `backend/pyproject.toml` (including `[tool.vercel.scripts]`), `backend/app/config.py` (every setting and its environment variable), `backend/app/cli.py` (the commands and flags), `frontend/next.config.ts`, `frontend/package.json` (scripts), `.github/workflows/*.yml` (the variables and secrets they read), `backend/README.md`, `frontend/README.md`, `tools/*/README.md`.

## Scope

You may edit `docs/DEPLOYMENT.md`, `docs/DEVELOPMENT.md`, `docs/ARCHITECTURE.md`, `.env.example` files, and the READMEs of `backend/`, `frontend/` and `tools/` **to correct statements only** (a wrong name, a missing step, a removed feature). No code, no configuration (`vercel.json`, workflows and scripts are the truth you check against: if one of them looks wrong, do not change it; report it). No new documents.

## Requirements

1. **Walk every instruction.** For each command in a code block of the three documents: run it if it is safe and local (`mise run dev`, `uv run ...`, `pnpm ...`, `node tools/...`, `python -m app.cli ... --help`), and check the output matches what the document says; if it is not safe to run (it needs Vercel, Neon credentials, or changes shared data), check by reading that the command, its flags and the files it names exist. Keep a table (in your report, not in the repository) of every command, whether you ran it or read it, and the result.
2. **Walk every name.** Every environment variable named in the documents and in the `.env.example` files must be read by the code (`config.py`, the CLI, the frontend, the workflows) under that exact name, with the meaning and the default the document gives; every variable the code reads that matters to a deployment (`DATABASE_URL`, `DATABASE_URL_UNPOOLED`, `SESSION_SECRET`, `APP_ORIGIN`, `TEST_TOKEN`, `API_URL`, `LOCK_TIMEOUT_MS`, `TRUSTED_PROXY_COUNT`, `TEST_MODE`, the Vercel ones, and any other you find) must be documented, with whether it is required online. Every path, script, workflow and port named must exist.
3. **Walk the deployment story end to end** as the owner would: import the repository in Vercel, the preset and root directory, the services of `vercel.json`, the Neon integration and the two connection strings, the build hook that migrates and seeds in Production only, the variables to set and where (project settings, GitHub), what the first deployment should show, how to verify it (and the smoke test of `tools/smoke/` if that directory exists in `main` by then: read its README; if it does not exist, say nothing about it), the nightly reset workflow and its `DEMO_URL` and `TEST_TOKEN`, rotating the Neon password. For every claim about Vercel or Neon behavior that you cannot verify from the repository, mark it in the document with the phrase "not verified in a real deployment" (the first deployment has not happened), and do not remove existing caveats.
4. **Order and completeness.** The steps must be in an order that works (a variable needed by the first build is set before it, not after), nothing the owner must do is missing (for example setting the GitHub repository variable and secret, or checking that Hobby limits allow the build), and nothing described has been removed from the code. Add the missing step or remove the stale one; keep the document's style and length (tight, tables and short lists).
5. **Ask yourself what would go wrong** for a person following the documents on a first deployment (a missing variable, a wrong region, a cold start, a failing migration, a blocked origin check because `APP_ORIGIN` does not match the deployment URL, cookies on a preview URL) and make sure the troubleshooting hints, if any, say how to see it and what to do. Add at most one short "If something goes wrong" section to `docs/DEPLOYMENT.md` if none exists, built only from behavior you verified in the code (the error codes, the log lines and the health check).
6. **Report what you could not fix.** A configuration or code problem you find (for example a variable the code needs that no document or `vercel.json` provides) is not yours to change: list it in the report with the file, the line and why it matters. The supervisor decides.

## Acceptance criteria

`node tools/audit/docs-lint.mjs` exits 0 and from `backend/` `uv run pytest -q tests/docs` passes. The supervisor reads the three documents with the same eyes and re-checks a sample of the corrections against the code.

## Rules for this task

- Commit as you go, in small real steps (about 4 to 8 commits, one per document or per kind of correction). Conventional Commits, in English (`docs(deploy): ...`).
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory; never print a secret.
- Ports: use `WEB_PORT=3200 API_PORT=8200` for anything you start, and stop it when you finish; do not kill processes you did not start.
- If a command runs more than 3 minutes, interrupt it (esc) and look for the cause.
- If something is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the table of commands (ran or read), every correction you made (what was wrong and what it says now), every problem you could not fix and report, and any deviation or open question.
