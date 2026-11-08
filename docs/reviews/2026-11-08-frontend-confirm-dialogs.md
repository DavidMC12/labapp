# Review: frontend confirmation dialogs (task 032, 2026-11-08)

- **Branch:** `w2/confirm-dialogs`, by Worker 2 (7 commits, inside `frontend/` plus one line of `docs/TESTABILITY.md` that the brief asked for).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **Verified by the supervisor:**
  - the five frontend commands and the test id audit re-run with real exit codes in a detached checkout (707 tests in 74 files, 68 files and 301 ids audited, 0 problems); `typecheck` and `build` first failed on stale generated types left in `.next` by an earlier development server of the supervisor, and passed after removing it (the clean-clone check before the push is the guard against that);
  - the commit rules;
  - the dialog driven in a real browser against the running application: "Cancelar pedido" opens a modal `<dialog>` with the title "¿Cancelar el pedido PED-0001?" and the draft message, the first focus is "Volver", axe reports 0 violations with the dialog open, Escape and "Volver" close it and leave the order a draft, and "Sí, cancelar pedido" cancels it (the badge turns "Cancelado"); the screenshot shows the dimmed backdrop and the danger styling.
- **Not verified:** the focus returning to the opener after a real mouse click (the scripted click does not focus the button; the component reproduces the native behavior and a test asserts it).

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Minor | The loading spinner of the "Cancelar pedido" button was dropped (the dialog covers the screen while the request runs). | Accepted: no test or screen relied on it. |
| 2 | Minor | One line of `docs/TESTABILITY.md` is outside `frontend/`. | Accepted: the brief asked for it. |
