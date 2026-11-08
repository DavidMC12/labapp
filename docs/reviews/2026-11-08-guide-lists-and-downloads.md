# Review: the automation guide, sorting, downloads and response headers (task 060, 2026-11-08)

- **Branch:** `w2/guide-lists`, by Worker 2 (5 commits plus 3 for the review feedback; `docs/AUTOMATION_GUIDE.md` only).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge after the fixes below. No Critical findings.
- **What it adds:** "Sort the four lists" (the 14 sort buttons by list, what a click does, what to assert, a Playwright sketch for the state and one for the order of the rows, the traps), "Sorting the lists: `sort` and `direction`" (the API: fields, defaults, ties, normalization, `curl` examples with the first values on the seed), "Download the lists as CSV" (the export links, a download sketch, the three headers, the exact header line of each file, the formula guard, a `curl` recipe, a small RFC 4180 parser) and "The headers of every API answer" (with a `curl -i` recipe and a request sketch), plus the cross-references.
- **Verified by the supervisor:** the documentation linter and the documentation tests exit 0; the `curl` recipes and their claims were checked against the live API in the reviews of tasks 050, 052, 055 and 057 (the first values of every sort, the export headers, the CRLF endings, the formula guard on Acme's phone, the headers on a 200 and a 401, the contract and the Swagger page with only `nosniff`); the ids the sketches cite exist in `docs/TESTIDS.md`.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Important | The guide said the sort button has "no `data-state` otherwise"; the component writes `data-state="none"` on an unsorted column (only the `aria-sort` of the `<th>` disappears). A reader would have written an assertion that fails. | Fixed: the table says so, and the sketch now asserts `none` and the missing `aria-sort` on another column. |
| 2 | Important | Two sketches called `request.newContext()`; the `request` fixture of Playwright is an `APIRequestContext` with no such method. | Fixed: they import `request as pwRequest` from `@playwright/test`, create the context with it and dispose it. |
| 3 | Note | The Playwright sketches are labelled "illustrative, not run in CI" and were not run (no Playwright in the repository). | Accepted; they were checked against the ids and attributes of the real pages. |
