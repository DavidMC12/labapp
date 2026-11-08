# Review: frontend fixes from the second-agent review (task 067, 2026-11-08)

- **Branch:** `w2/review-fixes`, by Worker 2 (5 commits).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings left.
- **What it fixes** (the numbers are those of `docs/reviews/2026-11-08-batch-security-review.md`): the import form's file input is `disabled` while the request is in flight and its `onChange` does nothing then (finding 2); choosing another file clears the result text, the alert and the errors table (finding 6); the four lists keep the previous data on screen while the next sort, page or filter loads (`placeholderData: keepPreviousData`), with `aria-busy="true"` on the table region (`TableScroll` gets a `busy` prop), so the focused header button is no longer destroyed (finding 4); `APP_HEADERS_SOURCE` matches whole path segments, so `/apiary` and `/__test__x` keep the web headers (finding 11); the README, the "Sort the four lists" section of the guide (a click on the column that is already the sorted one flips it, and the focus stays on the button) and the practice catalog (rows J-43 and J-44 rewritten, rows I-47 to I-50 added for the kept focus).
- **Verified by the supervisor:** in a detached checkout, install, lint, typecheck, coverage, build, the audit tool tests, the test id audit and the documentation lint exit 0; the browser audit covers 60 states with 0 failures and 1041 Tab stops in each theme, the catalog unchanged. **The focus defect, measured again in Chromium:** before the fix, pressing Enter on a sort button left `document.activeElement` on `BODY` on the customers, orders, invoices and products lists; after it, the active element is the same button on all four. A script of the supervisor's own also showed that after choosing another file following a success the result text is gone (it stayed before), and re-checked the practice rows I-36, I-39, I-41, J-31, J-32, J-34 and J-42 in the real browser.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Note | When "Siguiente" is clicked onto the **last** page it becomes disabled, and Chromium removes the focus from a control that becomes disabled (the active element falls to `BODY`). This is the browser's behavior for a legitimately disabled control, not the remount loss. | Documented inside row I-48 with the 41-customer case (page 2 of 3). A later improvement could use `aria-disabled` instead of `disabled`. |
| 2 | Note | Typing into the search box in the probe needed real key events for React to see the input. | A detail of the test harness. |
