# Review: spec hardening (2026-10-31)

- **Branch:** `docs/spec-hardening`, 16 commits reviewed (documentation only), plus the fixes below.
- **Reviewer:** a second agent, read-only, run in the background at the same effort level as the author.
- **Verdict:** With fixes. No Critical findings. The reviewer re-ran the arithmetic of `docs/SEED.md`, checked the error catalog for duplicates and cross-references, and tested the test id pattern against every example in the repository; all of those checks passed.

## Important findings and what happened to them

| # | Finding | Disposition |
|---|---|---|
| 1 | The idempotency record lifecycle was under-specified (concurrent duplicates, which outcomes consume a key, storing card data in a fingerprint). | Fixed: atomic claim and second lookup after the lock, only outcomes that create a payment row consume the key, keyed hash of the body, no card data stored (SPEC section 6). |
| 2 | The order lock covered transitions but not edits. | Fixed: every mutation of an order locks it first (SPEC section 5). |
| 3 | A double submit returned a timing-dependent code. | Fixed: the version is checked under the lock, so the result is the same sequentially and concurrently. |
| 4 | The transport of `version` was not defined. | Fixed: body field for `PATCH`, `If-Match` for transitions, `ETag` on responses, and which record's version is checked. |
| 5 | Rate limits under `TEST_MODE=1` and behind the proxy were undefined. | Fixed: off when `TEST_MODE=1`, valid token defined, client IP derived from `X-Forwarded-For` with `TRUSTED_PROXY_COUNT`. |
| 6 | What a reset restores was incomplete. | Fixed: idempotency keys and rate-limit counters are cleared, sessions are kept (SPEC section 9). |
| 7 | The `failed` payment and the gateway-unavailable error could not be triggered. | Fixed: test card ending in `0003`, a gateway fault target, and a seeded failed payment. |
| 8 | `ORDER_TOO_MANY_LINES` was unreachable with 15 products. | Fixed: the cap is now 10 lines. |
| 9 | Default list order and seed timestamps were not fully deterministic. | Fixed: `created_at` then `id`, both descending, and seeded timestamps for users, customers and products. |
| 10 | `errorTestId` could not handle suffixed ids or select and textarea fields. | Follow-up task 004; the grammar and the kind table were fixed in `docs/TESTABILITY.md`. |
| 11 | Brief 001 had fragile defaults, an import-time guard and a wrong section reference. | The work had already been delivered; the issues are recorded as errata in the brief. |

## Minor findings

Applied: the application origin setting, the `Secure` cookie rule, the order of checks for every operation, malformed JSON and unknown references, lock timeout, the invoice email sent after commit, the customer row in the lock order, session expiry using the application clock, constant-time token comparison, tax wording, seed gaps (reference, versions, ids, gapless numbering, datasets), the `reason` vocabulary, card number formatting, spec wording fixes, a rounding-tie example in the seed, fault rules that never touch `/__test__/*` or the health endpoint, and the dispositions of the bootstrap record.

Deferred: a documentation lint in CI (recompute the seed totals, check code uniqueness, run the test id pattern over every id in the docs) once the CI of M1 exists.
