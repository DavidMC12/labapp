# Review: sortable column headers on the four lists (task 051, 2026-11-08)

- **Branch:** `w2/list-sorting-ui`, by Worker 2 (18 commits).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. One defect was found in review and fixed before the merge (below).
- **What it does:** a shared `SortableHeader` (a `<th scope="col">` with `aria-sort` only on the sorted column and a real `<button>` inside, with `data-state` and an `aria-hidden` arrow); the 14 sort buttons of the four lists with the ids of the brief; the list state in the URL (`?page=1&sort=name&direction=asc`, the default sort leaves both parameters out, invalid values fall back); a visually hidden `role="status"` announcement per list; a new "Creado" column on the customers list; the API calls and query keys carry the sort; 5 new browser-audit states (four sorted lists and one that clicks a header); the catalog regenerated.
- **Verified by the supervisor:** in a detached checkout, install, lint, typecheck, coverage (825 tests, lines 97.52 %), build, the three audit test files, the test id audit and the documentation lint exit 0; the browser audit covers 56 states with 0 failures in the light theme (catalog unchanged) and in the dark theme. Then a real-browser run against the live API (headless Chromium, clicks on the real headers): customers by name ascending and descending, orders by number, invoices by total (first click ascending, second descending: 768.90, 327.80, 197.97), products by price descending (LP-300, CH-ERG, PR-400); the URL, `aria-sort`, `data-state`, the status text and the order of the rows were right each time; a click on "Creado" went back to the default sort; the filters survived a sort; the page title stayed correct after each soft navigation; the three detail pages (customers, orders, invoices) rendered in about 0.65 s and stayed responsive.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Critical (caught in review, never merged) | Worker 2 found that a sort click is a soft navigation and App Router rewrites the document title, and fixed it with a `MutationObserver` created **per call** of `useDocumentTitle`. The detail pages mount two calls at once (`customers/[id]`, `orders/[id]`, `invoices/[id]`), and two observers with different titles rewrite the title against each other for ever: an infinite loop that froze the test run (three Vitest workers at 100 % CPU) and would freeze a real tab. | Fixed by Worker 2 on the supervisor's instruction: one observer for the whole document, a module-level desired title (the last mounted hook wins), a counter of mounted hooks, the observer attached to `document.head` (a navigation replaces the `<title>` element) and disconnected when the last hook unmounts; tests with two hooks at once (bounded by a spy on the writes) and with the disconnect. |
| 2 | Minor | The list URL keeps `page=1` (`?page=1&sort=name&direction=asc`, and `?page=1` for the default sort): that is the convention of the existing lists, which always write the page. | Accepted: consistent. The practice catalog will say so. |
| 3 | Minor | The JSDoc of `useDocumentTitle` sits above the module state, not above the function. | Accepted: cosmetic. |
| 4 | Note | The products list announces its default order as "Ordenado por Id, ascendente" (the id is not a column); the invoice list announces "Creada" (the label of its column). | Accepted. |

## Lessons

- A stuck test process is a signal, not a nuisance: three workers at 100 % CPU for minutes meant a real infinite loop in the code, found by looking at the process list.
- A global effect (an observer, a listener) created per hook call needs a single shared instance as soon as two calls can be mounted together.
