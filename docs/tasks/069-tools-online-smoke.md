# Task 069: a smoke test for the online demo

Assignee: Worker 1. Branch: `w1/online-smoke`. Reviewer: Supervisor.

**Base.** Branch from `main`.

## Goal

Nothing has been deployed yet. When the owner imports the repository in Vercel (`docs/DEPLOYMENT.md`), someone has to check, quickly and the same way every time, that the online demo works: the web pages, the API behind the same origin, the four demo users, the headers, the contract, and that the test controls stay closed without the token. Write that check as a small tool that runs against any base URL (the Vercel deployment, a preview, or the local stack), so it can be run by hand after a deployment and from GitHub Actions on demand.

## Read first

`docs/DEPLOYMENT.md` (what is deployed, the variables, the "Check the deployment" steps), `docs/SPEC.md` (sections 2 and 3: the users, the origin rule, the test token; section 8: the headers), `docs/AUTOMATION_GUIDE.md` (the test controls and the demo section), `tools/audit/README.md` and `tools/audit/resources.mjs` (the style of the existing Node tools: no dependencies, `node:test` for the pure parts), `.github/workflows/nightly-reset.yml` (how a workflow reads `DEMO_URL` and `TEST_TOKEN`) and `.github/workflows/ci.yml` (where the Node tool tests run).

## Scope

New files under `tools/smoke/` (the script, a pure helper module, its tests, a README), a new workflow `.github/workflows/smoke-online.yml`, one line in `.github/workflows/ci.yml` to run the new tests with the other tool tests, and a short section in `docs/DEPLOYMENT.md`. No new dependency (Node's built-in `fetch`, `node:test`). No change to the application.

## Requirements

1. **The tool** `tools/smoke/online-smoke.mjs`: `node tools/smoke/online-smoke.mjs --base https://example.vercel.app [--token <test token>] [--json]` (the token may also come from the environment variable `TEST_TOKEN`; never print it). It runs the checks below in order, prints one line per check (`ok` or `FAIL`, the name, and on failure the exact reason: the URL, the expected and the actual value), a summary, and exits 1 if any check failed (0 otherwise). A check that cannot run because an earlier one it depends on failed is reported as `skipped`, not as a pass. A global timeout of 10 s per request and a total of 3 minutes; a cold start can take several seconds, so a failed `GET /api/health` is retried up to 5 times, 5 s apart, before it counts as a failure.
2. **The checks** (each is a function of the base URL, small and independent where possible):
   - **Web:** `GET /` and `GET /login` answer 200 `text/html`; `/login` has the title `Iniciar sesión · LabApp`; the response carries `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` and a `Content-Security-Policy` (production deployments only: if the host is `localhost` or `127.0.0.1` the CSP check is skipped and says so); `GET /no-such-page` answers 404 with the title `Página no encontrada · LabApp`; `GET /icon.svg` answers 200 with an image type.
   - **API basics:** `GET /api/health` 200; `GET /api/openapi.json` 200 JSON with `openapi`, `paths` and the paths `/api/customers`, `/api/orders`, `/api/invoices`, `/api/customers/import`; `GET /api/docs` 200 `text/html`; both documents carry `nosniff` and no `Cache-Control`; `GET /api/customers` without a session is 401 with the `application/problem+json` code `UNAUTHENTICATED` and carries `nosniff` and `no-store`; `GET /api/nope` is 404 `NOT_FOUND` with the same two headers.
   - **The four users:** log in as each demo user with the password shown on the login screen (read it from `docs/SEED.md` or the SPEC, never from an environment); each answer is 200 and sets the cookie `labapp_session` (`HttpOnly`, `SameSite`, and `Secure` when the base is `https`); `GET /api/auth/me` with that cookie returns the right role. A wrong password is 401 `INVALID_CREDENTIALS`. Log out and check that the cookie no longer works.
   - **Reads through the web origin:** as Sales, `GET /api/customers` answers 200 with `total` and `items`, `GET /api/products` answers 200 with 15 items on a freshly seeded demo (if the number differs, report it as a `warning`, not a failure: the shared demo changes during the day); `GET /api/customers/export` answers 200 `text/csv` with the header line of the SPEC and `Content-Disposition`; a list with `?sort=name&direction=asc` answers 200; `?sort=bogus` answers 422.
   - **The origin rule:** a write with a **wrong** `Origin` (`https://evil.example`) is 403 `CSRF_ORIGIN_MISMATCH`; a write with no `Origin` is accepted by the rule (use `POST /api/auth/logout`, which is harmless, for this).
   - **The test controls stay closed:** `POST /__test__/reset` **without** the token answers 404 (and carries `nosniff`); with a **wrong** token also 404. If `--token` is given: `GET /__test__/clock` with the token answers 200; the tool does **not** call `reset` or `seed` (they change the shared data) unless `--allow-reset` is passed, in which case it calls `POST /__test__/reset`, expects 200, and then reads `/api/customers` as Sales and expects `total` 10.
   - **A write and its cleanup** (only with `--allow-reset`, because the data changes): create a customer with a unique name, read it back, and deactivate it (the demo has no delete), then check the list `total` grew by one.
3. **Pure helpers** in `tools/smoke/checks.mjs` (header assertions, the expected-cookie attributes, the problem-body check, the retry policy with an injected clock and fetch) with `node:test` tests that need no network: each helper passes a good case and fails a bad case with the right message.
4. **Prove it against the local stack, both ways.** Start the stack as `docs/DEVELOPMENT.md` says (in-memory API, `DATABASE_URL= DATABASE_URL_UNPOOLED= scripts/dev.sh`; ports 3000 and 8000 may be in use by another process: check first and use `WEB_PORT`/`API_PORT` if needed): the tool must exit 0 (with `--allow-reset` too: the local controls need no token when `TEST_MODE=1`, so the tool must handle "the controls answer 200 without a token" as the local case, reported as `info`, not as a failure). Then show it **fails** on a broken target: for example run it against a stack whose API answers 404 for `/api/health` (point `--base` at the web app alone with no API), or temporarily stop the API, and show the failing lines and exit 1. Put both outputs in the report.
5. **The workflow** `.github/workflows/smoke-online.yml`: `workflow_dispatch` only, with inputs `base_url` (required) and `allow_reset` (boolean, default false); it runs the tool with `TEST_TOKEN` from the repository secret; it must not run on push or schedule; it uses the same Node version as the other workflows. Validate the YAML.
6. **Docs.** `tools/smoke/README.md` (what each check proves, the flags, the exit codes, how to run it by hand and from Actions, why `reset` needs `--allow-reset`), and a short section in `docs/DEPLOYMENT.md` ("After the first deployment: run the smoke test") with the exact command.
7. **CI.** Add the new test file to the Node tool tests line of `.github/workflows/ci.yml` (the CI must run it; it needs no network).

## Acceptance criteria

From the repository root: `node --test tools/smoke/*.test.mjs` and the other tool tests, `node tools/audit/docs-lint.mjs`, `node tools/audit/testid-audit.mjs` pass; the tool run of requirement 4 (both outputs). The supervisor re-runs the tool against a local stack.

## Rules for this task

- Commit as you go, in small real steps (about 6 to 10 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory. Never print a token or a password except the public demo password of the seed.
- If a command runs more than 3 minutes, interrupt it (esc) and look for the cause.
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, the two outputs of requirement 4, and any deviation or open question.
