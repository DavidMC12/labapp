# Review: "Exportar CSV" links on the lists (task 053, 2026-11-08)

- **Branch:** `w2/csv-export-ui`, by Worker 2 (13 commits).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **What it does:** a plain `<a download>` link "Exportar CSV" on the customers, orders and invoices lists (`*-list-export-link`), with a pure `exportUrl` helper per feature that builds the `href` from the **applied** list state (`q`, `status`, `sort`, `direction`, plus `customer_id` on orders when the page reads it), never `page`, leaving out the defaults; `TEXT_LINK_CLASSES` exported from `Link` so the anchor shares the look of the other secondary links; one new audit state (`customers-list-filtered-export`); the catalog regenerated; a README paragraph.
- **Verified by the supervisor:** in a detached checkout, install, lint, typecheck, coverage (865 tests), build, the three audit test files, the test id audit and the documentation lint exit 0; the browser audit covers 57 states with 0 failures in both themes (catalog unchanged). Then a real-browser run (headless Chromium with downloads enabled, live API): for each list the link is an `<a>` with `download`, the `href` carries exactly the applied filters and sort and no `page`, text typed in the search box and not applied does not change it, and **clicking it downloads a real file** (`customers-20261108.csv`, `orders-20261108.csv`, `invoices-20261108.csv`) whose number of data rows equals the `total` the API returns for the same query (8, 1 and 3), CRLF line endings, header line first.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Note | The invoices list does not read `order_id` from the URL (the page has no such filter), so its export link never carries it; the brief said "plus `order_id`". | Accepted: the link carries only what the page applies. If the page ever reads `order_id`, the helper takes it. |
| 2 | Note | `TEXT_LINK_CLASSES` is a small refactor of `Link.tsx` (the same classes, now exported). | Accepted. |
