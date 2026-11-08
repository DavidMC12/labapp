# Task 052: CSV export of the lists (backend)

Assignee: Worker 1. Branch: `w1/csv-export`. Reviewer: Supervisor.

**Base.** Branch from `main` after task 050 (list sorting) is merged (the supervisor tells you).

## Goal

Downloading a file and checking its content is one of the exercises a test engineer must practice, and almost no demo application offers it. Add three read-only endpoints that export the customers, orders and invoices of the list filters as a CSV file, exactly as `docs/SPEC.md` section 8 ("CSV export") and the three API tables now define. This task is the backend only: the download links in the screens come later (task 053), and this task must not change any screen.

## Read first

`docs/SPEC.md`: section 8, the bullet **CSV export** (every rule in it is a requirement: read it twice), the `GET .../export` rows of the three API tables, and the **List** rules of the customers, orders and invoices (the export reuses their filters, their sort and their validation). Then, for each module, `routes.py`, `service.py` (how `list_*` validates `q`, `status` and the sort and builds the filters), the ports and adapters (`list` takes a `page` and a `page_size`), the response helpers of `app/openapi.py` (`documented_responses`), and `app/infra/clock.py` (the application clock: the file name date comes from it).

## Scope

You may edit under `backend/`: a new pure module `app/domain/csv_export.py`, the three modules (routes and services; avoid changing the ports: the export can read the rows page by page through the existing `list` with a larger `page_size`, such as 500, until a page comes back short), their tests, `backend/README.md` (a short "CSV export" paragraph with one `curl` example) and `docs/openapi.json` regenerated with the command `backend/README.md` gives. Do not edit `docs/SPEC.md`, the frontend, `tools/` or `tests/`. No new dependency (use the standard library, but write the escaping yourself: see requirement 1).

## Requirements

1. **The pure CSV writer** in `app/domain/csv_export.py`: a function that takes the header (a sequence of names) and the rows (sequences of values, each `str`, `int`, `Decimal`, `datetime`, `None`) and returns the text. Rules, all from the SPEC: fields separated by commas, lines end with CRLF (the last line too), a field is wrapped in double quotes when it contains a comma, a double quote, CR or LF and a double quote inside is doubled; `None` is an empty field; a `str` that starts with `=`, `+`, `-`, `@`, a tab or a carriage return gets a single quote in front of it **before** the quoting rules are applied (so `=1+1` becomes `'=1+1`, and `-5, x` becomes `"'-5, x"`); `Decimal` money has exactly two decimals, `datetime` is ISO 8601 UTC with a trailing `Z` and no fraction (`2026-10-31T14:30:00Z`), `int` is plain. Do not use `csv.writer` for the quoting of the formula rule; you may use it for the quoting if you prefer, as long as the tests below pass. The numeric columns are never given a quote.
2. **Three routes**, `GET /api/customers/export`, `GET /api/orders/export` and `GET /api/invoices/export`, declared **before** the `/{id}` routes so that `export` is not read as an id. They need a session, the same dependency the list uses (401 before anything else); any role may export. They accept the list's filter and sort query parameters and run the same validation with the same 422 answers (reuse the validation code of the list, do not copy it), and take no `page` (a `page` is ignored). They answer 200 with `text/csv; charset=utf-8`, `Content-Disposition: attachment; filename="<resource>-<YYYYMMDD>.csv"` where the date is the UTC date of the application clock (not the system clock), and `Cache-Control: no-store`.
3. **The rows and the columns** exactly as the SPEC lists them (customers `id,name,email,phone,tax_id,address,status,created_at,updated_at`; orders `id,number,status,customer_id,customer_name,subtotal,tax_rate,tax,total,invoice_id,created_at,updated_at`; invoices `id,number,status,order_id,order_number,customer_name,tax_id,subtotal,tax_rate,tax,total,created_at,updated_at` with the snapshot name and tax id). The rows are in the order of the list for the same `sort` and `direction`; the count equals the `total` of the list for the same filters. For a draft order the subtotal, tax and total are the computed ones the list shows (use the same summary the list builds, not a second calculation).
4. **OpenAPI.** Each route documents `200` with the media type `text/csv` (schema `string`) and the headers `Content-Disposition` and `Cache-Control`, plus the common error answers the list documents. Regenerate `docs/openapi.json`; the drift test passes.
5. **Tests.**
   - The writer: plain values, a comma, a double quote, an embedded CRLF and LF (an address), unicode (`Ñandú`, `日本`), `None`, each formula starter (`=`, `+`, `-`, `@`, tab, CR) with and without a comma, a value that is only `-`, money with 0, 1 and 2 decimals, a timestamp with and without a fraction, the CRLF at the end.
   - Each route: the header line; the number of rows equals the `total` of the list for the same filters (use more than 20 rows, so the export is proven not to stop at one page: replace the data with 45 rows); the rows follow the sort (`sort=name&direction=asc`); the filters (`q`, `status`; `customer_id` for orders; `order_id` for invoices); a `page` is ignored; the headers (`Content-Type`, `Content-Disposition` with the date moved by the test clock, `Cache-Control`); 401 without a session; the 422 of an invalid `status` and an invalid `sort` has the same body as the list; a customer whose name is `=HYPERLINK("http://x","y")` and whose address holds a line break comes out as the SPEC says, and the response parses back with `csv.reader` into the original fields (apart from the leading quote).
   - Every role (Admin, Ventas, Finanzas, Solo lectura) can export.
6. **README.** `backend/README.md`: a "CSV export" paragraph with one `curl` example that saves the file.

## Acceptance criteria

From `backend/`: `uv run ruff check .`, `uv run ruff format --check .` and `uv run pytest -q -W error --cov=app --cov-report=term` pass (the coverage floor holds). The supervisor also fetches the three files from a running server and opens them with a CSV parser.

## Rules for this task

- Commit as you go, in small real steps (about 8 to 12 commits: the writer, then each module, then the contract and the README). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, and any deviation or open question.
