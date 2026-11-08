# Task 046: hardening of the payment path (findings of the second-agent review)

Assignee: Worker 1. Branch: `w1/payments-hardening`. Reviewer: Supervisor.

**Base.** Branch from `main`.

## Goal

A background reviewer read the whole invoices and payments path (record: `docs/reviews/2026-11-08-payments-security-review.md`). It found no Critical issue; the two Important ones are already fixed. This task closes the cheap Minor findings and the test gaps it listed. No behavior visible to the API changes.

## Read first

`docs/reviews/2026-11-08-payments-security-review.md` (findings 3 to 7), `docs/SPEC.md` section 6 (invoices and payments, idempotency), `backend/app/modules/invoices/adapters/postgres.py` (`register_payment`, `_claim_key`), `backend/app/modules/invoices/adapters/memory.py` (the same logic in memory), `backend/app/modules/invoices/tables.py`, `backend/migrations/versions/` (read two existing migrations to copy their style and naming), `backend/tests/integration/test_invoice_concurrency.py`, `backend/tests/integration/` (how the other tests build an app on a random schema), `backend/tests/invoices/contract_store.py`.

## Scope

You may edit files under `backend/` only: the two invoice adapters, `tables.py`, one new migration, the tests, `backend/README.md` if a section needs a sentence. No new dependency. Do not change `docs/SPEC.md`, any route, schema, error code or message.

## Requirements

1. **One approved payment per invoice, enforced by the database.** A new Alembic migration adds a partial unique index on `payments (invoice_id) WHERE status = 'approved'` (name it `uq_payments_one_approved_per_invoice`), with a working `downgrade`. Declare the same index in `tables.py` so the metadata matches. The migration must not fail on a database that already has data (the demo database does): the seed has no invoice with two approved payments, say how you checked it. Add an integration test that a second approved row for the same invoice is rejected by the database (`IntegrityError`) and that a declined or failed row next to an approved one is allowed.
2. **The claim cannot crash on a concurrent expiry.** In `_claim_key`, after a conflict the code reads the stored key with `.one()`. If the conflicting row was deleted in that instant (an expired key purged by another request) the read finds nothing. Replace it so that an empty read retries the claim, at most 3 times, and the third failure raises the same lock-timeout style error the module already uses for an unavailable resource (read how `LOCK_TIMEOUT` is produced; if there is no clean way, raise the existing generic database error). Add a unit test with a fake connection or the existing test seams that forces the empty read once and shows the claim succeeds on the retry.
3. **Purge the expired keys of the invoice.** Today only the same key is purged when it is reused. Make `_claim_key` delete every expired key of that invoice (same `KEY_LIFETIME` cutoff) before the claim, in PostgreSQL and in the in-memory adapter, so a long-lived invoice cannot accumulate dead keys. Keep the behavior of a replay inside the 24 hours exactly as it is. Tests in the shared contract (`contract_store.py`) so both adapters run them: a key older than 24 hours is gone after a new payment attempt on the same invoice, a younger key still replays.
4. **A comment where the gateway is called** (`register_payment` in both adapters): one short comment saying that a real gateway that raised or timed out would need its own handling (a `failed` payment recorded outside the failed transaction), and that today only the fake gateway exists and the fault gateway raises nothing. No behavior change.
5. **The races, repeated.** In `test_invoice_concurrency.py`, the pay-versus-pay race and the pay-versus-cancel race each run once. Repeat each round `RACE_ROUNDS = 20` times in a loop with a fresh invoice (or a reset) per round, and assert the invariants every round: exactly one approved payment, the invoice and the order end `paid` or the order `cancelled` with the invoice `void`, never both, and no deadlock error. If one round takes more than a few seconds on a remote database, keep `RACE_ROUNDS` as a module constant and say so in the report; do not lower it to 1.
6. **Two missing end-to-end tests** (integration, they are skipped without `TEST_DATABASE_URL`): (a) a full payment over HTTP against the PostgreSQL stores (log in as Finance, pay an issued invoice by card and read the invoice back); (b) a payment that fails with 503 `LOCK_TIMEOUT` leaves its `Idempotency-Key` free: hold the invoice row lock in a second connection with a short `LOCK_TIMEOUT_MS`, send the payment, expect 503, release the lock, send the same key again and expect 201. Follow how the existing integration tests build the app.

## Acceptance criteria

From `backend/`: `uv run ruff check .`, `uv run ruff format --check .` and `uv run pytest -q -W error --cov=app --cov-report=term` pass (the coverage floor holds). The integration tests are skipped on your side (no database); the supervisor runs them against a real PostgreSQL. Say in the report which tests are integration-only.

## Rules for this task

- Commit as you go, in small real steps (about 8 to 12 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, which tests are integration-only, and any deviation or open question.
