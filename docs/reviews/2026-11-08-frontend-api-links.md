# Review: links to the API documentation on the login screen (task 044, 2026-11-08)

- **Branch:** `w2/api-links`, by Worker 2 (4 commits, inside `frontend/`).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **Verified by the supervisor:** the commands re-run with real exit codes in a detached checkout (763 tests, coverage 97.61 % of lines with the floor holding, lint, typecheck, build, test id audit and documentation lint with 0 problems); the commit rules; the two links in a real browser: they are plain anchors, `GET /api/docs` and `GET /api/openapi.json` through the web origin answer 200 with the right content types; the browser audit over 39 states in both themes, 0 failures; a screenshot of the login with the line "Para probar la API: Documentación interactiva · Contrato OpenAPI" under the demo users box.
- **After the merge:** the supervisor regenerated the test id catalog (three new ids on the login).

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Minor | The theme selector sits very close to the heading "Iniciar sesión" on the login. | Not from this task; noted for the polish pass. |
