# Review: serve the API contract and its documentation (task 041, 2026-11-08)

- **Branch:** `w1/serve-contract`, by Worker 1 (5 commits: three lines in `backend/app/main.py`, tests, two documentation lines).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **Verified by the supervisor:**
  - the backend commands and the contract command re-run with real exit codes on the branch merged with `main` (ruff, format, `pytest -q -W error`: 1531 passed, 1 expected failure, 211 integration tests skipped; the contract file does not change);
  - the commit rules;
  - a real server: `GET /api/openapi.json` answers 200 `application/json` and equals `docs/openapi.json` (21 paths, none under `/__test__`, one relative server, the `cookieAuth` scheme); `GET /api/docs` answers the Swagger UI page; `/docs`, `/openapi.json` and `/redoc` answer 404.
- **Note:** the Swagger UI loads its assets from a CDN (the FastAPI default); the page needs internet access, the JSON does not.

## Findings and what happened to them

None above Minor.
