# Review: frontend settings screen (task 025, 2026-11-07)

- **Branch:** `w2/settings-ui`, by Worker 2 (8 commits, all inside `frontend/`).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **Verified by the supervisor:**
  - the five frontend commands and the test id audit re-run with real exit codes in the worker's tree (575 tests in 60 files, 55 files and 267 ids audited, 0 problems);
  - the commit rules (author, attribution lines, Conventional Commits);
  - the data layer and the page read in full: the raw value is sent as typed, never trimmed or parsed; the server's `message` is shown next to the field; any other problem goes to the form alert; focus moves to the first error; the pending guard lives in a ref, so a double click is ignored;
  - the screen in a real browser against the running API, as Admin and as Sales, light and dark (screenshots), and driven by script: `" 7"` shows "El formato no es válido.", `"101"` shows "El valor debe estar entre 0 y 100.", `"7"` shows "Impuesto actualizado a 7.00 %." and the input keeps `7.00`;
  - the browser audit (axe plus test ids) on the two new states, in both themes, 0 failures. The states `settings-admin` and `settings-readonly` were added to `tools/audit/states.json` by the supervisor, since `tools/` is outside the worker's scope.
- **Found by the live run, not a defect of the screen:** a browser whose address is `127.0.0.1` gets 403 `CSRF_ORIGIN_MISMATCH` because the local application origin is `localhost`; the screen showed that answer in its alert, as designed.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Minor | The field error id is `settings-taxrate-error`, not `settings-taxrate-input-error` as the brief table said: the `Field` component builds it from the field id. | Accepted: it follows the existing pattern and is valid and unique. |
| 2 | Minor | While the session loads the page shows "Cargando…" and while the settings load "Cargando configuración…", both under the same id. | Accepted: the two never render together. |
