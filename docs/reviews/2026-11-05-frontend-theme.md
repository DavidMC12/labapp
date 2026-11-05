# Review: frontend "Libro mayor" light theme (task 013, 2026-11-05)

- **Branch:** `w2/libro-mayor`, by Worker 2 (26 commits, all inside `frontend/` plus the brief).
- **Reviewer:** Supervisor. The brief was reviewed by a second agent while the work was under way (2 Critical and 8 Important findings, sent to the implementer as corrections; see the brief).
- **Verdict:** With fixes in round 1, then ready to merge. No Critical findings in the code.
- **Verified by the supervisor:** the five acceptance commands re-run with real exit codes (243 tests, zero lint warnings, typecheck, production build); the tokens and the Button component read; the application run from a scratch checkout with the theme merged and **screenshots taken through a headless browser** of the login (desktop and phone), the customers list (desktop and phone), the detail and the edit form, compared with the chosen design; the same checks on a clean clone before pushing.

## What the work did well

Every color lives once in `globals.css` as a token and the components use only token utilities, guarded by two tests (contrast ratios of the listed pairs and a scan for literal colors), so the dark theme can be added by changing one file. The shell, the login, the badges, the ledger footer with its double rule and the serif headings match the design closely; the shell switches to a top bar on a phone and no page scrolls horizontally. The implementer kept every `data-testid` and every text, changed only the three test assertions the review allowed, and reported honestly what it could not see.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Minor | On desktop the ID fiscal code wrapped in the middle ("JUPI-" / "300210"). | Fixed: those cells do not wrap. |
| 2 | Minor | On a 390px phone the list table was crushed (names on eight lines, the last column cut). | Fixed: a minimum table width so the wrapper scrolls horizontally. |
| 3 | Minor | The customer form column was centered while every other page is left aligned. | Fixed: left aligned, 520px maximum width kept. |

Deferred: the dark theme (next task), a browser-level audit of the pages (axe and unique test ids per page), and the dev-only Next.js indicator that overlaps the bottom of the rail in development.
