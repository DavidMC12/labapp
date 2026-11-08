# Review: practice scenarios for the sort headers, the export links and the import screen, UI rows (task 065, 2026-11-08)

- **Branch:** `w2/practice-ui-rows`, by Worker 2 (5 commits; `docs/PRACTICE.md` only).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **What it is:** 13 UI rows in area I (`I-34` to `I-46`: the sort buttons, the order of the rows, page 1 and the filters, a sorted URL opened directly, an invalid `sort`, the `href` of the export links, the downloads, the clock in the file name, 320 px) and 15 UI rows in area J (`J-31` to `J-45`: the link by role, the permission notice, the disabled button, the good file, the table of errors, `.txt` and 120 KB, the recovery of the form states, a slow upload, 320 px). Every row was run by the worker in Chromium (real clicks, `DOM.setFileInputFiles`, `Browser.setDownloadBehavior`) before it was written.
- **Verified by the supervisor:** the catalog tests, `ruff`, the unit suite and the documentation linter exit 0. A script of the supervisor's own drove the real application in Chromium for the rows with new claims: I-36 (the Creado button starts descending, the first click writes `?page=1&sort=created_at&direction=asc` and "Ordenado por Creado, ascendente", the second leaves the bare `?page=1`), I-41 (an invalid `sort` falls back to the default list and the address bar keeps the URL), I-39 (page 1 of 2, the URL `?page=1&q=Pagina&sort=name&direction=asc`, the export `href`), J-31 for the four roles, J-32 (only the forbidden alert), and J-34, J-42 and J-43 with real files: all matched.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Note | On the plain customers list the Creado column is already the sorted one, so its first click flips it to ascending and the second returns the plain list. The brief and the guide assumed a first click in descending order. | The row (I-36) records what is observed. The guide's sentence about the first click is corrected in task 067. |
| 2 | Follow-up | Row J-43 documents that the previous result stays on screen after choosing another file. That is the defect of finding 6 of `2026-11-08-batch-security-review.md`, fixed in task 067. | Task 067 updates J-43 and J-44 to the new behavior and adds the rows for the kept focus. |
