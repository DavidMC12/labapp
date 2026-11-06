# Review: browser audit of the test id contract and accessibility (2026-11-06)

- **Branch:** `feat/browser-audit`, by the Supervisor (4 commits: `axe-core` as a frontend dev dependency, `tools/audit/browser-audit.mjs` with `states.json`, a CI job, the docs).
- **Reviewer:** none beyond the author: a small tool, verified by running it, in both directions. A second-agent pass can still be asked for.
- **Verified:** the audit run against the local application (16 states: login, home, the customers screens, the orders screens, the invoices placeholder; with several roles) reports 0 failures: no interactive element without a test id, no repeated id, and no serious or critical axe violation (WCAG 2.0 and 2.1, A and AA, which includes color contrast). A **negative check** against a deliberately bad page (a button without an id, an image without alternative text, a repeated id, a malformed id, an unlabeled input) reports the five problems and exits 1. The CI job was rehearsed locally with the same steps: a production build with the API address compiled in, both processes started, the audit run against `next start`.

## Notes

The browser audit is what the testability contract promised for the 100% goal: its measure is the list of states, so every new screen and notable state must be added to `states.json` (the invoices screens, in task 020, and the dark theme states). The states use the demo users and the fixed seed data, so the audit runs against the in-memory API or a freshly seeded database. Deferred: running the audit at a phone width and in the dark theme, and failing on moderate axe violations (printed as warnings today).
