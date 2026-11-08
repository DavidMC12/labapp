# Review: frontend new order from a customer (task 039, 2026-11-08)

- **Branch:** `w2/order-from-customer`, by Worker 2 (6 commits, all inside `frontend/`).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **Verified by the supervisor:**
  - the commands re-run with real exit codes in a detached checkout (762 tests in 76 files, coverage 97.61 % of lines with the floor holding, lint, typecheck, build, test id audit with 0 problems);
  - the commit rules;
  - the whole flow in a real browser against the running application: the customer detail of an active customer shows the link to `/orders/new?customer_id=2`; an inactive customer and the Finance role do not see it; the form with `customer_id=2` has "Beta Comercial Ltda." selected and "Crear pedido" enabled; with an inactive customer (5), an unknown one (999) it selects nothing and shows "El cliente indicado no está disponible para nuevos pedidos."; with `abc` the parameter is ignored; creating the order lands on the new draft `PED-0008` of that customer.
- **After the merge:** the supervisor regenerated the test id catalog (the customer detail has a new id).

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Minor | The same notice is shown for any failure to load the preset customer (500, network), not only for inactive and not found. | Accepted: the user can still choose a customer, and the page does not break. |
| 2 | Minor | Six commits instead of the eight to twelve of the brief. | Accepted: each one is a real step. |
