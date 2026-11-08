# Task 043: the automation guide, part 2 (test controls and the HTTP API)

Assignee: Worker 2. Branch: `w2/automation-guide-api`. Reviewer: Supervisor.

**Base.** Branch from `main` after the documentation linter (task 042) is merged (the supervisor tells you), or on top of your current branch until then. `main` already has the test controls, the idempotent payments and the committed contract.

## Goal

Part 1 of `docs/AUTOMATION_GUIDE.md` teaches how to drive the web UI. Part 2 teaches the other half of what makes LabApp a good automation target: the test-only controls (reset, seed, clock, faults) and the HTTP API with its contract. The reader writes API and end-to-end tests and needs recipes that work. Everything you write must be read from the code, the SPEC and the committed contract; never describe behavior you have not read.

## Read first

`docs/AUTOMATION_GUIDE.md` (part 1, to keep the style and to replace its "what is next" line), `docs/SPEC.md` sections 2, 3 (the test token, the controls, rate limits), 7, 8 and 9, `docs/ARCHITECTURE.md` ("Test-only controls"), `docs/openapi.json` and `backend/README.md` (the "Test controls", "Request controls" and "OpenAPI contract" sections), the code under `backend/app/modules/testcontrols/`, `backend/app/guards/`, `backend/app/modules/invoices/` (`routes.py`, `service.py`), `backend/app/errors.py`, `docs/SEED.md`, `docs/DEVELOPMENT.md`, `docs/DEPLOYMENT.md`.

## Scope

You may edit `docs/AUTOMATION_GUIDE.md` (add part 2 and update the closing section of part 1) and `README.md` / `README.es.md` (only if a link line needs a change). No other file. No code.

## Requirements

Add these sections after part 1, in English, tight, with tables and short lists. Every endpoint, field, status code and message must be exactly what the code does.

1. **Where the API is.** Base path `/api`, same origin as the web app, the session cookie `labapp_session` (how to log in with a request, the `Origin` rule of the CSRF check: which methods it applies to, what a missing `Origin` does, what a wrong one answers), the contract file `docs/openapi.json` and how to import it, the error format (`application/problem+json` with `code`, `detail`, `errors[]`, and the extra members of a payment problem), and the stable codes table pointer (SPEC section 7).
2. **Test controls.** A table of the seven endpoints (method, path, body, answer) from the code; the token (`X-Test-Token`, when it is needed: local `TEST_MODE`, online), what every answer looks like without it (404, and why), rate limits and the token. Then the **recipes** (each a short, working sequence with `curl` and one Playwright `request` sketch labelled "illustrative, not run in CI"): reset before a suite and what it keeps (sessions and the four users); `seed` with `empty` and `default`; move the clock to test `SESSION_EXPIRED` (advance beyond the session lifetime, read the lifetime from the code, then observe the notice on `/login?expired=1`) and card expiry; inject a 500 on a route a given number of times; inject latency; make the payment gateway unavailable once and see the `failed` payment; list and clear the rules; the limits (50 rules, 10 s latency, the clock range). State plainly what a rule cannot do (it matches a method and an exact path).
3. **Orders and invoices through the API.** The sequence for the three flows with `curl` (login, create a customer, create an order, add a line, confirm, issue the invoice, pay), the optimistic concurrency (`version`, `ETag`, `If-Match`: which routes take which), the payment idempotency (`Idempotency-Key` format, the replay header, what consumes a key, 24 hours, the declined and unavailable outcomes and why a retry needs a new key), pagination and filters of the lists.
4. **Isolating tests.** Three patterns with their trade-offs: reset before each suite, reset per worker with the shared online demo (what is unsafe), creating your own data with unique names. A note on parallel runs and the per-IP rate limit.
5. **The online demo.** What differs from local (the token, the nightly reset at 03:17 UTC, shared data, the preview deployments), taken from `docs/DEPLOYMENT.md`; say that it is not deployed yet if it is still true.
6. **Close.** Replace the "what is next" line of part 1 with a short pointer to part 2 and a list of what to read next.

## Acceptance criteria

- Every endpoint, status code, header, field name and message in the new sections exists in the repository and is exactly as written (the supervisor checks a sample against the code and runs some of the `curl` sequences against a live server; a command that does not work is a defect).
- No claim about behavior that you did not read. When something is unknown, say it is not verified.
- The documentation linter of task 042 passes on the guide (links and ids).

## Rules for this task

- Commit as you go, in small real steps (about 8 to 12 commits, one per section). Conventional Commits, in English (`docs(guide): ...`).
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If something is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the sections you could not complete and why, and any deviation or open question.
