# Review: frontend phone header (task 038, 2026-11-08)

- **Branch:** `w2/phone-header`, by Worker 2 (7 commits, all inside `frontend/`).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **Verified by the supervisor:**
  - the commands re-run with real exit codes on the branch merged with the current `main` (745 tests in 76 files, coverage floor holds at 97.57 % of lines, lint, typecheck, build, test id audit with 0 problems);
  - the commit rules;
  - the browser audit over 39 states, the phone and tablet ones included, in both themes: 0 failures, no page scrolls sideways;
  - screenshots at 390 pixels in both themes: the header takes three rows (brand, a single scrolling navigation row with the current section kept in view and a fade on the right edge, and the user row with the name and role, a compact theme select and "Salir") instead of five rows and about 340 pixels; before it was a third of the screen.
- **Not verified:** the scroll-into-view in a slow phone; covered by a test with a stubbed `scrollIntoView`.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Minor | The scroll effect also runs when the session loads, so a deep link scrolls the row correctly. | Accepted: it is the right behavior. |
| 2 | Minor | Only the container padding shrank, not the link padding. | Accepted: the links look right. |
