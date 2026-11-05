# Audits

`testid-audit.mjs` is a static check of the test id contract in [docs/TESTABILITY.md](../../docs/TESTABILITY.md). It parses every `.tsx` file under `frontend/src` (tests excluded) and fails when:

- a `button`, `a`, `input`, `select`, `textarea`, `form`, `table`, `h1`, `h2`, `h3` or `dialog`, a `Button`, `Input`, `Select`, `Textarea` or `Link`, or any element with `role="alert"` or `role="status"`, has no `data-testid` or `testId`;
- a literal id does not match the grammar in `frontend/src/lib/testid.ts` (the pattern is read from that file, so there is one definition);
- an id expression cannot be checked statically. A constant or property whose name ends in `testId` is accepted: its value is checked by the `TestId` type at compile time.

Template ids such as `` `customers-list-row-${id}` `` are checked with a sample number. That an id appears once in a rendered page is a property of the DOM, so it belongs to a browser audit, not to this one.

```bash
node tools/audit/testid-audit.mjs                       # audit the frontend
node --test tools/audit/testid-audit.test.mjs           # test the audit itself
```

It needs the frontend dependencies installed (it uses the TypeScript compiler from `frontend/node_modules`). CI runs both commands in the frontend job.
