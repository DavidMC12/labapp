# Review: a keyboard audit, visible focus and no keyboard trap (task 062, 2026-11-08)

- **Branch:** `w2/keyboard-audit`, by Worker 2 (8 commits).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **What it does:** the browser audit now walks every audited state with real Tab key presses (DevTools `Input.dispatchKeyEvent`, never `.focus()`), after the state is ready. A pure module (`tools/audit/keyboard.mjs`, with its own tests) judges the walk: a tabbable element that takes the focus with no visible focus indicator (the computed style focused against the same element unfocused, over outline, box shadow, border, background, color and text decoration; WCAG 2.4.7), a keyboard trap (five presses on one element, or 60 presses that never leave the content; WCAG 2.1.2) and a visible tabbable element the walk never reaches. Elements of the dev server's own tools, closed dialogs, `inert` elements and the element a modal makes unreadable are left out. The summary line counts the Tab stops, and `--no-keyboard` skips the walk.
- **Verified by the supervisor:** in a detached checkout, install, lint, typecheck, coverage, build, the audit tool tests (including the new file), the test id audit and the documentation lint exit 0; the browser audit covers 60 states with 0 failures and **1041 Tab stops walked** in each theme, the catalog unchanged. **The negative proof, run independently:** with a scratch rule `*:focus-visible { outline: none !important; box-shadow: none !important; }` appended to `globals.css` (never committed, reverted), three states produced 49 failures that name each element (`app-nav-customers-link`, `customers-form-name-input`, `customers-form-submit-button`, ...), exit 1. The run time grew by about 4 % (47.8 s to 49.6 s in the worker's measurement).

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Note | The unfocused snapshot is compared with the focused one by computed style, not by contrast: a ring whose color is invisible against its background would pass. | Accepted and documented in the README: contrast is the job of axe and the design tokens. |
| 2 | Note | Headless Chromium visits its own chrome between cycles of the Tab order, so the walk presses through that phase and ends when the focus is back on the first element. | Accepted: documented in the code and the README; the 1041 stops per theme and the negative proof show the walk reaches the page. |
| 3 | Note | The worker's closing message had garbled text in its notes (a glitch of the model); the facts in the report matched the commits and the runs. | Accepted. |
