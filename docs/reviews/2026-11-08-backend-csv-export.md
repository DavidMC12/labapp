# Review: CSV export of the lists, backend (task 052, 2026-11-08)

- **Branch:** `w1/csv-export`, by Worker 1 (8 commits: the pure writer, the three routes, the contract and the README).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **What it does:** `GET /api/customers/export`, `GET /api/orders/export` and `GET /api/invoices/export` as `docs/SPEC.md` section 8 defines them: a pure RFC 4180 writer with the spreadsheet-formula guard (`app/domain/csv_export.py`, no `csv.writer`), the same filters, sort and validation as the lists (the list validation is reused through a shared helper, not copied), no paging (every page is read through the existing `list` port with a larger page size), the file name dated with the application clock, `Cache-Control: no-store`, and the `text/csv` answer documented in the OpenAPI contract.
- **Verified by the supervisor:** `ruff check`, `ruff format --check` and the unit suite with the coverage floor exit 0 (1759 passed, coverage 87.52 %). Then a live check against a running server: the three files fetched with a read-only user, headers exact (`text/csv; charset=utf-8`, `attachment; filename="<resource>-<YYYYMMDD>.csv"`, `no-store`, `X-Request-Id`), no byte order mark, CRLF endings, the header line of the SPEC for each resource, the number of rows equal to the `total` of the list (11, 7 and 3), a `page` parameter ignored, 401 without a session, the 422 body of an invalid `status` equal to the list's. A customer created on purpose with the name `=HYPERLINK("http://x","y")`, an address with a line break, a comma and quotes, and a phone starting with `+` came back as the SPEC says and the address parsed back to the original through `csv.reader`; the invoices sorted by total descending came out in order.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Note | A phone number that starts with `+` (the usual international format) is exported with a leading quote, because the SPEC applies the formula guard to every text column. | Accepted: it follows the SPEC; it is the safe default and is documented as a practice case. |
| 2 | Note | The helper that documents the CSV answer lives in `app/domain/csv_export.py` because `app/openapi.py` was outside the brief. | Accepted. |
