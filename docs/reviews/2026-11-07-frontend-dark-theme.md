# Review: frontend dark theme (task 023, 2026-11-07)

- **Branch:** `w2/dark-theme`, by Worker 2 (17 commits, all inside `frontend/`).
- **Reviewer:** Supervisor. The brief had been reviewed by a second agent before the work started; its findings on the rail label and the current link, the token test parser, the single selector instance and the no-flash script were sent to the worker as corrections and applied.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **Verified by the supervisor:**
  - the five frontend commands and the test id audit re-run with real exit codes in the worker's tree (541 tests, 50 files, 253 ids, 0 problems);
  - the commit rules (author, attribution lines, Conventional Commits, no leaks);
  - the screens in a real browser against the running app, in both themes and at 1280 and 390 pixels of width: login, customers, order detail, shell and phone layout (screenshots read one by one);
  - the browser audit (axe, serious and critical fail) over the 16 states in the **light and the dark theme**, both with 0 failures, with the choice pinned through `localStorage` before the page loads;
  - the served HTML: the no-flash script is in the `<head>`, static, and sets `data-theme` only for `light` and `dark`.
- **Not verified:** the system-dark path with a real operating system preference (the emulated media query was checked by screenshot only); Safari and Firefox rendering of the `<option>` popup, autofill and scrollbars.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Minor | With blocked storage the selector applies the attribute but cannot remember the choice, and a controlled select shows "Sistema" again. | Accepted: blocked storage is rare, the page keeps working and follows the choice until reload. |
| 2 | Minor | The "Facturar" button sits tight under the order card. | Not from this task (task 020); noted for the polish pass. |

Accepted deviations: two extra tokens (`rail-active`, `rail-active-ink`), added by the supervisor's correction because the current link of the rail used `paper`, which is almost the rail color in the dark theme (1.08 to 1).
