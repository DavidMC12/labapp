# Review: practice rows for the hostile and malformed import files (task 068, 2026-11-08)

- **Branch:** `w1/practice-hostile`, by Worker 1 (4 commits; `docs/PRACTICE.md`, area J).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **What it is:** 17 API rows `J-46` to `J-62`, every one marked as run: an unclosed quote in the last column, in a middle column and at the end of the file, text after a closing quote (all a whole-file `INVALID_FORMAT` with nothing created), a bare quote inside an unquoted field and a doubled quote (both valid and stored as written), a lone `\r`, mixed line endings, a BOM at the start and in the middle, a plain form field named `file`, two `file` parts (the last wins), an empty filename, a part named differently, a NUL byte, a record of 20 000 cells and 200 rows of the longest values (413).
- **Verified by the supervisor:** the catalog tests, `ruff`, the unit suite and the documentation linter exit 0. A script of the supervisor's own re-ran the new rows against a live server with `curl -F`: the three unclosed-quote files and the bare quote (task 066), and J-52 to J-61 (the lone CR, mixed endings, the BOM at the start and in the middle, the plain field, two parts, the empty filename, the part `other`, the NUL byte, the 20 000-cell record in 10 ms) all matched. J-62 was confirmed by the worker's run (a file of 200 rows with all five columns at their maximum lengths is about 125 KB); my own test file had only two columns and stayed under the limit, which is a mistake of my script, not of the row.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Note | A lone carriage return is accepted as a line end although the SPEC names CRLF and LF. | Documented as observed in J-52, which says the application is wider than the SPEC. |
| 2 | Note | The SPEC defines `REQUIRED` for a missing or empty `file` part; a plain form field named `file` answers `INVALID_FORMAT` (J-56) and an empty filename with valid content `INVALID_FORMAT` (J-58). | Accepted: a coherent reading, written down. |
| 3 | Note | Two `file` parts: the SPEC says "one file part"; the last one wins, which it does not specify. | Documented in J-57. |
