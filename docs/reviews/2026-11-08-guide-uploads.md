# Review: the automation guide, uploading a file (task 063, 2026-11-08)

- **Branch:** `w1/guide-uploads`, by Worker 1 (6 commits; `docs/AUTOMATION_GUIDE.md` and the description of the guide in both READMEs).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **What it adds:** "Uploading in the UI" (the ids of `/customers/import` in a table, the states `idle` to `loading` to `success` or `error`, when each happens, the traps, and Playwright sketches with `setInputFiles` and an in-memory buffer for a good file, a rejected file and a file too large), "Uploading over the API" (`curl -F`, the part name `file`, a `request.post` multipart sketch, the answer shapes, the limits, the line numbers, all-or-nothing, the `Origin` rule), a worked export and import round trip, and the cross-references and the READMEs' description of the guide.
- **Verified by the supervisor:** the documentation linter and the documentation tests exit 0. The `curl` recipes were run as written against a live server and matched the guide's output exactly: the good upload (201, the three headers, id 11), the rejected file (the exact 422 body), the line numbers after a blank line and a quoted line break (`rows[6].name`), the round trip (ten `CUSTOMER_EMAIL_TAKEN` entries from `rows[2]` to `rows[11]`) and the renamed file (created 10, ids 11 to 20). The Playwright sketches use only APIs that exist and the ids and attributes of the real page (checked against `docs/TESTIDS.md` and the page the supervisor drove in Chromium with real files in task 059).

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Note | The brief said that `curl` and `request` "must add `Origin`". The server (SPEC section 3) only rejects a write whose `Origin` is **present and different**; a request without it is accepted. Worker 1 wrote the true rule, with a link to section 10, instead of the brief's. | The brief was wrong; the guide is right. |
| 2 | Note | The Playwright sketches and the browser behaviour were not run by the worker (no Playwright in the repository). | Accepted: labelled "illustrative, not run in CI"; the page behaviour was verified in task 059. |
| 3 | Note | The 409 for an email taken between the validation and the insert is not reproduced live. | Accepted: it is in the SPEC and the backend README, and the integration test covers two concurrent imports. |
