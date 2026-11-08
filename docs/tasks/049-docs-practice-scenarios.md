# Task 049: a catalog of practice scenarios for the test automation

Assignee: Worker 2. Branch: `w2/practice-scenarios`. Reviewer: Supervisor.

**Base.** Branch from `main`.

## Goal

LabApp exists so that a QA engineer can practice test automation against a clean, well specified application. The automation guide (`docs/AUTOMATION_GUIDE.md`) teaches the tools; this task writes the other half: **what to test**. A catalog of scenarios, organized by flow and by technique, each with the exact expected result taken from the specification, so the reader can pick one, automate it and know what "pass" means. It is documentation only. You do not write automated tests and you do not touch `tests/`.

## Read first

`docs/SPEC.md` (all of it: the flows, the permission matrix, the error codes and messages, the concurrency and idempotency rules, the test-only controls), `docs/SEED.md` (the data every run starts with), `docs/TESTIDS.md` (the generated catalog of test ids per page), `docs/AUTOMATION_GUIDE.md` (style and how the controls are used), `docs/TESTABILITY.md`. Read the code only to confirm a behavior the spec leaves open.

## Scope

You may create `docs/PRACTICE.md` and edit `README.md` / `README.es.md` (one sentence each, next to the sentence that links the automation guide in the "run it" section) and `docs/AUTOMATION_GUIDE.md` (one pointer sentence at its end). No code, no `tests/`, no other file. Write in English.

## Requirements

1. **Structure of `docs/PRACTICE.md`.** A short introduction (what the catalog is, how to read a row, the legend of levels and techniques), a **learning path** (an ordered list of about 12 scenarios from the easiest to the hardest, each linking to its row), then one section per area:
   - A. Customers (flow 1): create, edit, deactivate and reactivate, search and pagination, validation and boundaries of every field, duplicate email, version conflict.
   - B. Orders (flow 2): draft, lines (add, edit, remove, limits), confirm (stock, inactive customer, empty order), cancel (draft and confirmed, stock given back, frozen tax rate), ship, the state transitions that must be refused, filters and the list of one customer.
   - C. Invoices and payments (flow 3): issue (tax id required, one per order), pay by card, transfer and cash, the decline card, amount mismatch, the idempotency key (replay, reuse with another body, expiry), the gateway unavailable, cancelling an invoiced order voids the invoice.
   - D. Roles and permissions: the matrix of the four roles against each action, as a table of 403 and 2xx expectations.
   - E. Session and security: login, wrong password, session expiry (clock control), the `Origin` rule, unauthenticated API access.
   - F. Concurrency and resilience: optimistic locking (`version`, `If-Match`), two payments at once, pay against cancel, injected faults, injected latency, the rate limit.
   - G. Accessibility, responsive and appearance: keyboard-only use of each flow, focus after a dialog closes, page titles, the skip link, the theme (light, dark, system), the 320 px and phone layouts, tables that scroll.
   - H. Test data and isolation: reset and seed, the clock, running tests in parallel (what is safe).
2. **Rows.** Each scenario is a table row with these columns: `ID` (area letter and number, for example `B-14`), `Level` (`UI`, `API` or `Both`), `Scenario` (one sentence), `Steps` (three steps at most, with the real test ids or endpoints in backticks), `Expected` (the exact status code, error `code`, message in Spanish and the test id of the alert or of the element, copied from the spec or the code), `Technique` (equivalence class, boundary value, state transition, error guessing, decision table, concurrency, accessibility) and `Level of difficulty` (1 easy, 2 medium, 3 hard). Target about 120 rows in total; do not pad: a row that restates another with a different value belongs in a boundary-value row of the same group.
3. **Every row is true.** Every status code, error code, message, field name, number and test id must be exactly what the specification, the generated catalog or the code says. The documentation linter (`node tools/audit/docs-lint.mjs`) checks the test ids you cite and the links; it must pass. For each API row, run it against a local API (`DATABASE_URL= DATABASE_URL_UNPOOLED= scripts/dev.sh`, in-memory data) with `curl` and add the mark `✔` to the `ID` cell of the rows you ran and found as written (use `curl` from a script you keep outside the repository). Aim to run at least 40 API rows. A row you did not run has no mark; a row where the behavior differs from the spec is not silently corrected: stop and put it in the report with the request, the answer you got and the spec text.
4. **Seed-aware.** Rows that depend on the seed name the exact record (for example "customer 4 is inactive", "order 3 is confirmed", "the invoice `FAC-0001`") as `docs/SEED.md` states, and say when a reset is needed first.
5. **A closing section** "What is deliberately not here": the app has no seeded bugs (a decision of the project owner) and the catalog does not list defects to find; it lists behaviors to confirm.
6. **Pointers.** One sentence in each README, next to the one that links the automation guide, and one sentence at the end of the automation guide.

## Acceptance criteria

`node tools/audit/docs-lint.mjs` exits 0 and the file's table rows are well formed (the same number of columns in every row of a table). The supervisor re-runs a sample of at least 15 of the API rows with `curl` against a live server and checks a sample of UI rows against the generated catalog and the screens; a row that is wrong is a defect to fix, not a note.

## Rules for this task

- Commit as you go, in small real steps (about 8 to 10 commits, one per area). Conventional Commits, in English (`docs(practice): ...`).
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the number of rows per area, how many API rows you ran (and the list of rows that differ from the spec, if any), the exact commands you ran with their exit codes, and any deviation or open question.
