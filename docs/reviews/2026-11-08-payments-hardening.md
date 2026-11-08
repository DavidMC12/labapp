# Review: hardening of the payment path (task 046, 2026-11-08)

- **Branch:** `w1/payments-hardening`, by Worker 1 (9 commits).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **What it does:** closes the Minor findings and the test gaps of the second-agent review (`docs/reviews/2026-11-08-payments-security-review.md`): a partial unique index `uq_payments_one_approved_per_invoice` (migration `0005`), a claim of the idempotency key that retries when the conflicting row is purged in that instant (at most 3 times, then 503 `LOCK_TIMEOUT`), the purge of every expired key of the invoice on a new payment attempt (both adapters), a comment where a real gateway would need its own error handling, the two payment races repeated 20 times, and two new end-to-end tests over HTTP.
- **Verified by the supervisor:** `ruff check`, `ruff format --check` and the unit suite with coverage exit 0 (1605 passed, 217 skipped, coverage 87.87 % against the floor of 85 %). The integration tests that cannot run without a database were run by the supervisor against a real PostgreSQL (Neon, random schema): the nine invoice integration files, 61 tests, all passed in 19 minutes, including the pay-versus-pay and pay-versus-cancel races (20 rounds each), the new partial-index tests, the full card payment over HTTP and the lock timeout that leaves its key free. The migration was read: one `create_index` with a `downgrade`; the demo seed has no invoice with two approved payments (a test pins it).

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Note | Worker 1 rebased its branch onto the newer `main` while working. | Accepted: its own branch, no pushed history changed. |
| 2 | Note | In the pay-versus-cancel race "exactly one approved payment" holds only when the payment wins; the test asserts both consistent endings (paid with one approved payment, or cancelled with a void invoice and none). | Accepted: the right invariant. |
| 3 | Minor | The 20-round race tests take 3.5 minutes each against a remote database (they are seconds in the CI container). | Accepted; `RACE_ROUNDS` is a module constant. |
