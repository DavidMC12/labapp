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

## Follow-up: the invoice screens against this backend (2026-11-08, after the merge)

- The screens of task 020 were driven in a real browser against the running application (not a mock): the list, the detail of an issued, a paid and a read-only view, in both themes (screenshots read one by one).
- The payment form was driven by script: the declined card shows "La pasarela rechazó el pago. Prueba con otra tarjeta." and keeps the form; the unavailable gateway shows its message and keeps the form; the approved card shows "Pago aprobado.", the invoice turns "Pagada", the form disappears and the history gains one row per attempt (5 rows after the 2 seeded ones plus 3 attempts). Each declined or failed attempt took a new idempotency key, as the policy requires.
- The browser audit now covers 21 states (the four invoice states replace the placeholder), in both themes, 0 failures.
