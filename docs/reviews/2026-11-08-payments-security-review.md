# Review: invoices and payments path (second-agent security review, 2026-11-08)

- **Scope:** the whole invoices module, the order side it touches, the guards and auth, at `main` `496cf4c`. Read-only review by a background Reviewer (no code run).
- **Verdict of the Reviewer:** With fixes. No Critical.
- **Strengths confirmed:** role checks run before the loader and before any side effect; money is `Decimal` end to end with half-up rounding; the idempotency claim, the payment, the invoice and order updates and the stored response are one transaction; the lock order (order, invoice, customer, products ascending) has no inversion; only the last four digits of a card reach the database and the 422 handler never echoes input.

## Findings and what happened to them

| # | Severity | Finding | Verified | Disposition |
|---|---|---|---|---|
| 1 | Important | Cancelling a **confirmed** order overwrote its frozen tax rate with the current one, so the order and its voided invoice disagreed after Admin changed the rate. | Yes, both adapters and the tests that pinned it. | Fixed: only a draft takes the current rate when cancelled (`fix(orders): keep the frozen tax rate when a confirmed order is cancelled`); SPEC sections 5 and 6 say so; the contract and route tests now assert the rate is kept; the PostgreSQL contract passes against Neon. |
| 2 | Important | A transfer `reference` with a NUL byte passed the length check and failed in PostgreSQL with a 500, while the in-memory store accepted it. | Yes (`has_control_character` was not applied to it). | Fixed: any control character is `INVALID_FORMAT` on `reference` (`fix(invoices): reject control characters in a transfer reference`); six new tests fail without the fix. |
| 3 | Minor | `.one()` after `ON CONFLICT DO NOTHING` can raise if the conflicting expired row is deleted in that instant. | Reasoned, very rare. | Task 046. |
| 4 | Minor | No partial unique index guarantees one approved payment per invoice. | Yes. | Task 046. |
| 5 | Minor | Declined payments and expired keys can grow without bound on one invoice (public demo credentials). | Yes; the nightly reset and the rate limit bound it in practice. | Task 046 purges the expired keys of the invoice on pay; a cap on attempts is not added (see the brief). |
| 6 | Minor | A gateway that raises (not the fake one) would give a 500 and no `failed` payment; the fault gateway commits in its own connection while the locks are held. | Yes; only live when test controls are on. | Noted in code by task 046 (comment); no behavior change. |
| 7 | Minor | A malformed `If-Match` beats a valid replay; the HMAC key of the idempotency fingerprint is `session_secret`; no `statement_timeout`; the race tests run once. | Yes. | The `If-Match` order and the dedicated secret are noted and left as they are; the race tests are repeated in task 046. |

## Declined to judge by the Reviewer

- The behavior of the Neon pooler under disconnects, the deployment settings and the frontend.
