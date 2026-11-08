# Review: site icon and failing-resource audit check (task 047, 2026-11-08)

- **Branch:** `w2/site-icon`, by Worker 2 (7 commits: the icon, its test, the audit check and docs).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **Verified by the supervisor:** in a detached checkout, `pnpm install --frozen-lockfile`, lint, typecheck, coverage, build, the three audit test files, the test id audit and the documentation lint all exit 0; the browser audit with the dev servers (in-memory API) covers 39 states with 0 failures in the light theme (the catalog is unchanged against `docs/TESTIDS.md`) and in the dark theme. The built HTML carries `<link rel="icon" href="/icon.svg?…">`. Worker 2 also proved the check fails both ways: with the icon removed the light run exits 1 with one failure per state.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Note | Worker 2 measured that headless Chrome never asks for `/favicon.ico` and reports the declared icon as an `Other` response, so the network check of the brief could not catch a missing icon. It added a probe (`iconFailures` in `tools/audit/resources.mjs`) that fetches the icon the page declares, or `/favicon.ico` when it declares none, as a real browser would. | Accepted: a justified deviation, covered by unit tests, and it is what made the negative proof possible. |
| 2 | Minor | `states.json` and `tools/audit/resources.mjs` were outside the file list of the brief. | Accepted: the brief required both changes (the `expectStatus` field and the pure function). |
