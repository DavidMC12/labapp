# Review: generated test id catalog (2026-11-08)

- **Branch:** `feat/testid-catalog`, by the Supervisor.
- **Reviewer:** a second Claude process in the background, read-only.
- **Verdict:** With fixes (no Critical), all applied, then merged.
- **Verified by the supervisor:** the Node tests of the audit arguments (10 pass); the catalog generated twice on a fresh application gives the same file, and the same file from a production build (`next start`, as CI runs it) as from the development server; the audit over 21 states in both themes, 0 failures.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Important | The `home` state captured the page after one counter loaded; a slow runner would have recorded loading ids and failed the catalog diff on an unrelated change. | Fixed: every state waits until nothing is loading (`aria-busy` or a loading status) before the ids and axe are read, and fails if it never settles. |
| 2 | Minor | A trailing blank line in the generated file. | Fixed. |
| 3 | Minor | `--catalog` could write a partial file (`--only`, a state that did not render, a missing value). | Fixed: bad arguments exit with code 2, nothing is written when a state did not render; three more tests. |
| 4 | Minor | A failing diff was hard to act on and a crashed audit was reported as "out of date". | Fixed: separate messages and a pointer to the README. An uploaded artifact was left out: the diff is printed in the log. |
| 5 | Minor | Noise: the shell ids repeat in 20 states; `row-10` sorted before `row-2`. | Fixed: the shell is listed once; natural order, independent of the locale. |
| 6 | Minor | Extraction gaps: input type, dev-tools filter. | Fixed (input type from the property, same filter as the interactive check); the explicit-role limitation is documented. |
| 7 | Minor | The header was inaccurate about numbers, hidden elements and states reached only after an interaction. | Fixed. |
| 8 | Minor | A possible race between two states that share a `waitFor` id. | Fixed: a blank document is loaded between states. |
