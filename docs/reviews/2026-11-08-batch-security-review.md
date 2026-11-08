# Review: second-agent review of the import, export, sorting, headers and payments hardening (2026-11-08)

- **Scope:** everything added since the payments review (`496cf4c`) up to `42667e2`: the customers CSV import (backend and screen), the CSV export, the sorting of the lists, the API response headers, the OpenAPI examples, the payments hardening and the web security headers. Read-only review by a background Reviewer that could not run code (it read the installed Starlette and FastAPI sources).
- **Verdict of the Reviewer:** With fixes. No Critical. Strengths it confirmed: the import write path is one statement in one transaction with uniqueness from the index (a race becomes a 409); multipart edge cases (a part without a filename, duplicate parts, the filename never stored or echoed) cannot crash; the export writer is pure and the formula guard covers every text column; `sort` and `direction` are enforced twice and only dictionary lookups reach SQL; wrapping the middleware stack keeps FastAPI's own layers and covers the 500; the title hook cannot loop; the URL parsing is an allowlist; there is no HTML sink.

## Findings and what happened to them

| # | Severity | Finding | Verified by the supervisor | Disposition |
|---|---|---|---|---|
| 1 | Important | `csv.reader` runs with `strict=False`: an unclosed quote swallows the following rows into one field and the import answers **201 with rows silently lost**; `"a"b` becomes `ab`. | Yes, reproduced with `csv.reader`: the second row vanished into the address; `strict=True` raises. | Task 066. |
| 2 | Important | The import form lets the file be changed while the request is in flight: `aria-busy` drops early, the button re-enables, and the answer of file A discards file B. | Yes, read in `ImportForm.tsx` (the input is not disabled, `onChange` sets `idle` unconditionally). | Task 067. |
| 3 | Important | The export reads 500-row pages, each its own transaction with its own `COUNT(*)` and `OFFSET`: not a snapshot (an insert between pages repeats or skips a row), quadratic cost, no row limit. | Yes, by reading the three services and the adapters. | Task 066: one port method per module that reads every match in **one** statement. |
| 4 | Important | The focused sort button is destroyed on every uncached sort (the page shows the loading text while `isPending`): keyboard focus falls to `<body>` (WCAG 2.4.3). The Tab-walk audit cannot see it. | **Yes, in a real browser:** pressing Enter on a sort button left `document.activeElement` on `BODY` on the customers, orders, invoices and products lists. | Task 067: keep the previous data while the next arrives, `aria-busy` on the table, and a real-browser proof. |
| 5 | Important | Test gap for hostile import input (a form field named `file`, two `file` parts, an empty filename, a lone `\r`, a NUL byte, a BOM in the middle, a record of tens of thousands of cells, the interplay of the 100 KB and the 200-row limits, an unclosed quote). | Yes: the cases are not in the suite. | Task 066. |
| 6 | Minor | Stale results stay visible under `data-state="idle"` after choosing another file. | Yes, same code. | Task 067. |
| 7 | Minor | Two concurrent imports with overlapping emails in different orders can deadlock (SQLSTATE `40P01`) and answer 500. | By reading (only `55P03` is mapped). | Task 066 maps it to the retryable 503 `LOCK_TIMEOUT`; the SPEC row now says "or a deadlock". The rows are **not** reordered: the ids follow the file order. |
| 8 | Minor | Ids are not guaranteed consecutive on PostgreSQL under concurrency. | Reasonable. | The SPEC now says "increase in file order and are consecutive unless another request inserts at the same moment". |
| 9 | Minor | The import route documents the wrong 400 (`MALFORMED_JSON`); a malformed multipart body gets FastAPI's own 400. | By reading. | Task 066 documents and pins the real answer. |
| 10 | Minor | Migration 0005 builds the unique index with no duplicate preflight; a live database could fail the deploy build with an unreadable error. | Reasonable. | Task 066 adds a preflight with a readable message. |
| 11 | Minor | `APP_HEADERS_SOURCE` is a prefix match: `/apiary` or `/__test__x` would lose the web headers. | By reading the pattern. | Task 067 (whole path segments). |
| 12 | Minor | A comment sits on the wrong branch (orders adapters: "a confirmed order keeps the rate frozen" above the draft branch). | Yes. | Task 066. |
| 13 | Note | No index serves the non-default sorts (`COLLATE "C"`, the cast of the number, `total`). | Agreed: fine at demo size. | Accepted. |

## Declined to judge by the Reviewer

- PostgreSQL's `lower()` against Python's for exotic characters; the Unicode policy for emails (the SPEC defines no normalization; invisible format characters pass the control-character rule, which predates this batch); whether Chromium handles `<a download>` on a non-2xx answer; whether Vercel compiles the negative-lookahead `source` as intended; the documents, the audit tooling and the platform limits.
