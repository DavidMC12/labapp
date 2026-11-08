# Task 033: tests that keep the documents and the code in agreement

Assignee: Worker 1. Branch: `w1/docs-consistency`. Reviewer: Supervisor.

**Base.** Branch from `main` after tasks 021, 022 and 024 are merged (the supervisor tells you), or on top of your current branch until then.

## Goal

`docs/SPEC.md` and `docs/SEED.md` are the contract that the owner's tests rely on ("values here are the contract"). Nothing checks that the code still says what the documents say. Write tests that read the documents and compare them with the code, so that a change to one without the other fails CI. These are ordinary pytest tests in `backend/tests/docs/`; they only read files (the repository root is found from the test file) and call the application's pure code.

## Read first

`docs/SEED.md` (all of it), `docs/SPEC.md` sections 4, 5, 6 and 7 (the error tables and the field error table), `backend/app/domain/` (money, numbering, labels, permissions), `backend/app/modules/*/seed.py`, `backend/app/errors.py`, `backend/app/modules/*/rules.py`, `backend/app/domain/orders.py`, the existing tests of the seeds.

## Scope

You may create files under `backend/tests/docs/` (a package with a small `markdown.py` helper that parses the pipe tables of a Markdown file into rows of cells) and add a short section to `backend/README.md`. You may not edit the documents or the application code: when a test finds a real disagreement, **do not fix it and do not weaken the test**: mark that single test `xfail(strict=True)` with the reason, and list it in your report with both sides of the disagreement (the supervisor decides which side is right). No new dependencies.

## Requirements

1. **Markdown tables.** `markdown.py` reads a file and returns the tables under a given heading as lists of dictionaries keyed by the header cells, with the backticks of the cells removed. Unit-test it on a small inline example (alignment row, an empty cell, a cell with a pipe inside backticks is not required).
2. **The seed matches SEED.md.**
   - Users: the four emails, names and roles of the table equal the demo users of the code.
   - Customers: the ten rows (id, name, email, tax id or none, active or inactive) equal `seed_customers()`.
   - Products: the 15 rows (id, SKU, name, price, stock) equal `seed_products()`.
   - Orders: the seven rows (number, customer, status, lines, subtotal, tax, total) equal `seed_orders()`; each order's totals are **recomputed** with `app.domain.money.compute_totals` from its lines and the rate 10.00 and must equal both the document and the code (this checks the half-up rounding notes of the document too).
   - Invoices and payments: the three invoices and four payments (invoice number and status per order, the payment id, method, status, reference) equal `seed_invoices()` and `seed_payments()`.
   - The numbering notes: after the seed the next order number is `PED-0008`, the next invoice `FAC-0004` and the next payment id 5.
3. **Error codes.** Collect every code in the "Code" column of the tables of SPEC sections 3 to 7 (`` `UPPER_SNAKE` `` in a table row that also has an HTTP status or a Spanish message). Then: (a) every code appears in the application code (a string literal in `backend/app/`), except a short explicit list of codes that exist only as a rule of the document (say which and why in the test); (b) every error code that the application raises (the `ApiError(...)` code literals and the code constants of `app/errors.py`, the rules modules and the guards) appears in the SPEC; (c) the HTTP status and the Spanish message of each code in the document equal the ones of the code where the code builds them in one place (the `rules.py` functions, `app/errors.py`, the domain errors): compare by calling those functions.
4. **Field error codes.** The table of field-level codes in SPEC section 7 (`REQUIRED`, `TOO_SHORT`, ...) equals the code table in `app/errors.py` (the messages with their `{min}` and `{max}` placeholders).
5. **Labels.** The label table of SPEC section 7 (order, invoice and payment states, payment methods, roles) equals `app/domain/labels.py`.
6. **Permissions.** The role table of SPEC section 2 equals the permission matrix of `app/domain/permissions.py` for every action and role.
7. **Order transitions.** The transition table of SPEC section 5 equals `next_status` of `app/domain/orders.py` for every pair of state and action.
8. **README.** A short "Documents and code" section in `backend/README.md`: what the tests check and what to do when one fails (change the document and the code together).

## Acceptance criteria

From `backend/`, all of these pass (a test marked `xfail(strict=True)` counts as passing):

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest -q -W error
```

## Rules for this task

- Commit as you go, in small real steps (about 10 to 14 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, every `xfail` with both sides of the disagreement, and any deviation or open question.
