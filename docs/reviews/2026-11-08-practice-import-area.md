# Review: practice scenarios for the customers import (task 061, 2026-11-08)

- **Branch:** `w1/practice-import`, by Worker 1 (5 commits: the area letter in the catalog tests and four groups of rows).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **What it is:** area **J. Customers import (file upload)** of `docs/PRACTICE.md`: 30 API rows (the good upload, the whole file wrong, a row wrong, the emails, who may upload and what is stored, and the exported file that is not an import file), every one marked as run, an introduction on `curl -F` and on files made up on the fly, and a step in the learning path. The catalog tests accept the letter `J` and require the area to have at least 24 rows. No row differs from the specification.
- **Verified by the supervisor:** the unit suite with the coverage floor and the documentation linter exit 0. Then a script of the supervisor's own ran 22 of the rows against a live in-memory API with `curl -F`: the good upload and the sequence (J-1, J-3, J-4), the minimum and maximum name (J-14, J-17), the short row (J-18), the errors in file order (J-19), the line numbers after a blank line and a quoted line break (J-20), the cap of 100 entries (J-21), nothing created (J-22), the emails (J-23 to J-25, including the first occurrence of an email in a row that has another error), the permission matrix and the 403 before the invalid file (J-26), 401 (J-27), 413 (J-28), the formula text and the leading quote stored as given and exported (J-29) and the exported file that cannot be imported (J-30, both as it is and with only `name,email`): all matched. Three of my own checks failed because of my script (a fixture email that exists in the seed, a dependent row, and the export order), not because of the catalog.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Note | The area has API rows only. | The UI rows (the import screen, the sort headers and the export links) are added by a later task. |
