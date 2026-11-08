# Review: frontend titles, skip link and landmarks (task 031, 2026-11-08)

- **Branch:** `w2/titles`, by Worker 2 (8 commits, inside `frontend/` plus the one line of `docs/TESTABILITY.md` that the brief asked for).
- **Reviewer:** Supervisor.
- **Verdict:** With one fix by the supervisor (below), then ready to merge. No other Critical or Important findings.
- **Verified by the supervisor:**
  - the five frontend commands and the test id audit re-run with real exit codes in a detached checkout (691 tests in 73 files, 66 files and 299 ids audited, 0 problems);
  - the commit rules;
  - in a real browser against the running application: the title of 12 screens (`Resumen`, `Clientes`, `Cliente Beta Comercial Ltda.`, `Pedido PED-0003`, `Factura FAC-0001`, `Productos`, `Configuración`, the 404 page and more, each followed by ` · LabApp`), the skip link as the first Tab stop of the login and of the shell (in the development server the Next.js dev overlay takes the very first Tab; the production build has no overlay), and the landmarks.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Important | The title of the login page stayed "LabApp" in a real browser: the hook runs in the outer component, and the framework puts the default title back when the content below the Suspense boundary resolves. The unit tests passed because jsdom does not do that. | Fixed by the supervisor: a server `login/layout.tsx` exports the title (the root template adds ` · LabApp`), and the browser audit now asserts the title of every state, so a title can no longer regress unnoticed. |
| 2 | Minor | The root layout metadata is not tested directly (importing it pulls the CSS through Vitest). | Accepted: the template is covered through the not found page and, now, through the browser audit. |
| 3 | Minor | One line of `docs/TESTABILITY.md` is outside `frontend/`. | Accepted: the brief asked for it. |
