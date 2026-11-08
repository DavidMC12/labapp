# Review: practice scenarios for sorting, CSV export and response headers (task 057, 2026-11-08)

- **Branch:** `w1/practice-lists`, by Worker 1 (5 commits: the area letter in the catalog tests, three groups of rows, the learning path pointer).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **What it is:** area **I. Lists: sorting, CSV export and response headers** of `docs/PRACTICE.md`: 33 API rows (14 on sorting, 12 on the CSV export, 7 on the response headers), every one marked as run, and the catalog tests (`test_practice_catalog.py`) accept the letter `I`, with a test that the area has at least 30 rows. No row differs from the specification.
- **Verified by the supervisor:** the unit suite with the coverage floor and the documentation linter exit 0 (the catalog tests check the new rows' codes, messages, endpoints and statuses). Then a script of the supervisor's own ran about 50 checks covering rows I-1 to I-33 against a live in-memory API (the first values of every sort, the defaults of `direction`, the 422 of an invalid or empty `sort` and `direction` on the four lists, a tie broken by id, the accent order, filters with sort, page 2 under a sort, the exact header line and first data row of the three exports, the file name moving with the clock, 21 rows in an export beyond one page, `page` ignored, the formula guard, RFC 4180 quoting, 401, the 422 equal to the list's, the four roles, and the headers on a 200, a 401, a 404, a 422, a 413, the contract, the Swagger page and a path outside `/api/`): all matched. One check of mine failed because of my own mistake (I expected ascending order in an export that follows the list's descending order); the file's values were exactly the row's.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Minor | Row I-11 ("`number` compares as an integer, not as text") cannot tell the two orders apart with four-digit numbers: `PED-0009` before `PED-0010` is also the text order. | Accepted: the row states what is observed and the rule of the SPEC; the unit tests of the backend prove the integer comparison with numbers of different length. |
| 2 | Note | The phone of customer 1 (`+1 555 ...`) is exported with a leading quote, because it starts with `+` (the SPEC rule for every text column). | Accepted; it follows the SPEC and the guide explains why. |
| 3 | Follow-up | The area has API rows only. | The UI rows for the sort headers and the export links are added later. |
