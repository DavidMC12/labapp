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

## Browser audit

`browser-audit.mjs` opens every state of `states.json` in a headless Chrome (through the DevTools protocol, no extra package besides `axe-core`), logs in as the state's user, waits for the state to render and fails when:

- an interactive element (`a[href]`, `button`, `input` other than `hidden`, `select`, `textarea`, `summary`, a `tabindex` of 0 or more, or one of the listed roles) is visible and has no `data-testid`;
- a `data-testid` is used twice on the page, or does not match the grammar;
- axe-core reports a **serious or critical** violation of WCAG 2.0 or 2.1 level A or AA (lesser ones are printed as warnings).

A state can have `steps` to reach something that needs an interaction (a confirmation dialog): `"steps": [{ "click": "<test id>", "waitFor": "<test id that must become visible>" }]`; the audit clicks, waits, and then checks the page as it is. A state can have a `viewport` (`{ "width": 390, "height": 844 }`) to be audited as a phone or a tablet, and `"catalog": false` to leave it out of the catalog when it only repeats the ids of another state. Every state also fails when the page scrolls sideways. A state can also have a `title`, the exact document title the page must have.

It prints every state it covered: the 100% goal is measured over those states, so a screen that is not in `states.json` is a gap of the audit. **Add a state for every new screen and every notable state of it** (an empty list, an error, a detail page of a fixed seed record).

```bash
scripts/dev.sh                                  # or any running API and web app
CHROME_BIN=/usr/bin/chromium node tools/audit/browser-audit.mjs
node tools/audit/browser-audit.mjs --only orders-list,orders-new --base http://localhost:3000
node tools/audit/browser-audit.mjs --theme dark   # the same states with the dark theme pinned
```

`--catalog <file>` writes every test id found in every state, with the element that carries it, as Markdown. The committed copy is [docs/TESTIDS.md](../../docs/TESTIDS.md); CI regenerates it in the light run and fails with a diff when it is out of date, so **adding or renaming an id means regenerating it** (start the application on a fresh seed, `DATABASE_URL= DATABASE_URL_UNPOOLED= scripts/dev.sh`, then run the command above with `--catalog docs/TESTIDS.md`).

`--theme light|dark` stores the explicit choice of the theme selector in `localStorage` before every page loads, so the axe contrast check runs against each voice of the design. CI runs the audit twice, once per theme. A color that is only wrong in one theme fails only that run.

It needs a running application (the states use the demo users and the fixed seed data, so run the API in memory mode: with `DATABASE_URL` empty, or against a freshly seeded database) and Chrome or Chromium (`CHROME_BIN` or the usual paths). CI builds the web app, starts both processes and runs it, once per theme, in the `browser-audit` job.
