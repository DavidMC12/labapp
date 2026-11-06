# Review: frontend invoices and payments screens (task 020, 2026-11-06)

- **Branch:** `w2/invoices-ui`, by Worker 2 (22 commits, all inside `frontend/`).
- **Reviewer:** Supervisor.
- **Verdict:** With fixes in round 1, then ready to merge. No Critical findings.
- **Verified by the supervisor:** the five frontend commands and both audits re-run with real exit codes on the branch merged onto the current `main` (495 tests, zero lint warnings, typecheck, production build, test id audit with 0 problems); the commit rules; the card privacy rules by reading the code and by a search (no console, storage, cookie or window use for card data, `autocomplete="off"` on the card fields, the card fields cleared after a paid payment, the request body carrying only the fields of the chosen method); the submit flow and the idempotency key handling read in full.
- **Not verified yet:** the screens against a real backend and in a browser, because the backend of invoices and payments (task 019) does not exist yet. That check (a live test of the data layer, screenshots, and the new states in the browser audit) must be done when it lands.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Important | After any HTTP answer except a network error the form took a new idempotency key. A 500, 502 or 504 (for example a platform timeout after the gateway approved) says nothing about whether the payment was recorded, so a retry with a new key could charge twice instead of replaying. | Fixed: the key is kept when there is no answer, on 429, and on any status of 500 or more except `PAYMENT_GATEWAY_UNAVAILABLE`; it is replaced after 201, 402, 409, 422 and the gateway-unavailable 503. Eight tests pin the policy. |
| 2 | Minor | `crypto.randomUUID()` exists only in secure contexts, so the form would throw over plain http on a LAN address. | Fixed: a helper falls back to a version 4 UUID built from `crypto.getRandomValues`, tested in both branches. |

Accepted deviations: three extra heading ids required by the audit, the wording of the closed-invoice notes, a "Fecha" column in the payment history, and "Tarjeta" as the default method.
