# Review: backend invoices and payments (task 019, 2026-11-08)

- **Branch:** `w1/invoices-backend`, by Worker 1 (13 commits, inside `backend/app/modules/invoices/`, `backend/app/modules/orders/` and the tests).
- **Reviewer:** Supervisor. The brief had been through two rounds of the background Reviewer, and the second round's corrections were sent to the worker while it worked.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **Verified by the supervisor:**
  - the four backend commands re-run with real exit codes in a detached checkout of the branch (ruff, format, `pytest -q -W error`: 1232 passed, 127 integration tests skipped without a database);
  - the commit rules (author, attribution lines, Conventional Commits);
  - the application started for real and driven over HTTP: issuing the invoice of `PED-0002` gives `FAC-0004` with `Location` and `ETag: "1"`, and the body equals the literal example of the spec; paying with the approved test card gives 201 with `ETag: "2"`, the same request again replays it with `Idempotency-Replayed: true`, the order becomes `paid` at version 3; the same key with another body is 422 `IDEMPOTENCY_KEY_REUSED`; the declined and the unavailable cards give 402 and 503 as problem documents carrying `payment_id` and `reason`, and the attempts appear in the payment list; `NaN` in the amount and a `text/plain` body are 422, never a 500; a wrong amount is `PAYMENT_AMOUNT_MISMATCH`; Sales cannot issue (403); cancelling the invoiced order voids the invoice;
  - the in-memory `register_payment` read in full: the order of checks, the early key lookup with the 24 hour expiry, the gateway call under the lock, `mark_paid` before the invoice changes, the response stored with the key.
- **Not verified yet:** the screens of task 020 against this backend (done after the merge) and the PostgreSQL concurrency of the same port (task 021).

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Minor | The docstring of `InvoiceStore` says the invoice row is locked `FOR UPDATE`; the design is `FOR NO KEY UPDATE` (a plain `FOR UPDATE` deadlocks with the key claim). | Passed to task 021, whose first commit fixes the docstring. |
