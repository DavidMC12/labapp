# Review: repository bootstrap (2026-10-31)

- **Scope:** the 15 commits that bootstrapped the repository: `.gitignore`, toolchain pins, license, both READMEs, `docs/SPEC.md`, `docs/ARCHITECTURE.md`, `docs/TESTABILITY.md`, `.env.example`, the commit-standards workflow and `tests/README.md`.
- **Reviewer:** a second agent, read-only, run in the background at the same effort level as the author.
- **Verdict:** With fixes. No Critical findings.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Important | The CI commit-range check passed silently when the range was invalid. | Fixed before merge: strict range resolution, tested locally in seven scenarios. |
| 2 | Important | Playwright auth-state ignores were anchored to the repository root. | Fixed before merge: patterns now match at any depth; `.vercel/`, `next-env.d.ts` and others added. |
| 3 | Important | Docs described unreleased features in the present tense. | Fixed before merge: marked as planned for M1. |
| 4 | Important | Payment retry and idempotency rules were not implementable. | Addressed in the spec-hardening branch; residual gaps closed after a second review (SPEC section 6). |
| 5 | Important | Concurrency and versioning had gaps. | Addressed in the spec-hardening branch; residual gaps closed after a second review (SPEC section 5). |
| 6 | Important | Error and authentication contract incomplete. | Addressed in the spec-hardening branch; residual gaps closed after a second review (SPEC sections 3 and 7). |
| 7 | Important | Seed data was not deterministic. | Addressed in the spec-hardening branch; residual gaps closed after a second review (`docs/SEED.md`). |
| 8 | Important | `TEST_MODE` was described inconsistently. | Addressed in the spec-hardening branch; residual gaps closed after a second review (guard table in ARCHITECTURE, env example). |
| 9 | Important | The test id contract could not be turned into a lint rule. | Addressed in the spec-hardening branch; residual gaps closed after a second review (grammar, pattern, "interactive" definition). |
| 10 | Important | Display formats were not deterministic. | Addressed in the spec-hardening branch; residual gaps closed after a second review (UTC and explicit `Intl` options, SPEC section 8). |

Minor findings: the attribution regex was anchored to line starts (fixed); timeout and concurrency were added to the workflow (fixed); pinning actions by commit SHA is deferred; reordering the first commits was declined because it would change the reviewed SHAs; the author email was switched to the GitHub noreply address before publishing; the remaining small spec gaps, the email notice, the rate-limit exemption, the health endpoint, the PostgreSQL pin and the axe wording were settled in the spec-hardening branch.

The reviewer set aside, as approved decisions, the stack choices, the business rules themselves, free-tier behavior, repository settings and the pinned tool versions.
