# Task 062: a keyboard audit (visible focus and no keyboard trap)

Assignee: Worker 2. Branch: `w2/keyboard-audit`. Reviewer: Supervisor.

**Base.** Branch from `main`.

## Goal

The browser audit runs axe on every state, and axe cannot judge two things a keyboard user lives with: whether the element that has the focus **looks** focused (WCAG 2.4.7, Focus Visible), and whether the Tab key can get out of everywhere (WCAG 2.1.2, No Keyboard Trap). The application was designed with a visible focus style and native controls; nothing proves it yet, and a new component could silently lose it. Add the check to the browser audit, with a proof that it can fail, so that every audited state is walked with the Tab key in both themes.

## Read first

`tools/audit/README.md`, `tools/audit/browser-audit.mjs` (how a state is loaded, the `steps`, the network window and the pure checks in `resources.mjs`: follow that pattern), `tools/audit/resources.mjs` and its tests, `frontend/src/app/globals.css` (the focus rules, the tokens of both themes, the focus rule of `[role="region"][tabindex]`), `docs/TESTABILITY.md`, and the success criteria 2.4.7 and 2.1.2 of WCAG 2.1 (the criteria, not a library).

## Scope

You may edit `tools/audit/browser-audit.mjs`, a new pure module next to `resources.mjs` (for example `tools/audit/keyboard.mjs`) with its tests (`node:test`, the same style as the existing ones), `tools/audit/README.md`, `docs/TESTABILITY.md` (one sentence: the audit now walks every state with the keyboard), and, only if the check finds a real defect, the frontend files that fix it (classes and CSS only: no `data-testid`, text, DOM order or behavior change). No new dependency.

## Requirements

1. **The walk.** For every audited state, after the state is ready (and after its `steps`), collect the tabbable elements and walk them with real Tab key presses through the DevTools `Input.dispatchKeyEvent` (not by calling `.focus()`): press Tab up to N times (a constant, 60) or until the focus leaves the page content and returns to the start (the browser chrome, `document.body` again, or the first element again). Record, for each stop, the focused element (its `data-testid`, or tag plus accessible name when it has none), whether it is inside the same document, and its visibility.
2. **Visible focus.** For each stop, decide whether the element has a visible focus indicator by comparing its computed style **focused** with the style of the same element **not focused**: any difference in `outline-style`/`outline-width`/`outline-color`, `box-shadow`, `border-top-color`/`border-top-width`, `background-color`, `color`, `text-decoration-line`, or an `outline-style` other than `none` with a width above 0, counts as visible; when there is none, the element fails with `no visible focus indicator`. Take the unfocused snapshot of every tabbable element before the walk (one pass over the list), the focused one during it; both through `getComputedStyle`. Elements that take the focus without being interactive (a `tabindex="-1"` target such as the alert that receives the focus programmatically) are not part of the Tab walk; a scrollable region with `tabindex="0"` is (the project's `TableScroll`).
3. **No keyboard trap and sane order.** A failure `keyboard trap` when five consecutive Tab presses leave the focus on the same element while it is not the last tabbable one, or when 60 presses never leave the content although there are fewer tabbable elements; a failure when a tabbable element that is visible in the state is never reached in the walk (compare the walk with the list of tabbable elements, ignoring elements inside a closed `<dialog>` and those with `inert`). The order itself is not judged.
4. **The pure part** (`keyboard.mjs`): functions that take plain data (the snapshots, the stops, the list of tabbable elements) and return the failure strings, so the logic is unit tested without a browser: a visible-focus decision for each property family, a state with no indicator, a trap, an unreached element, a clean walk. Tests for each.
5. **Output.** A failure per problem with the state name, the element and the reason, in the same format as the other checks; the summary line says how many Tab stops were walked in total. The check runs in the default audit (CI) and can be skipped with a `--no-keyboard` flag documented in the README for a quick run.
6. **Prove it both ways.** Run the browser audit in both themes with the check on (`tools/audit/README.md`, in-memory API with `DATABASE_URL= DATABASE_URL_UNPOOLED= scripts/dev.sh`): it must pass. Then temporarily remove the visible focus of one control (for example set `outline: none; box-shadow: none` on the primary `Button` focus rule, or the focus rule of `TableScroll`) in a scratch change you do **not** commit, run one theme and show that the audit fails on the right element and state; restore it. If the check finds a real defect on the unmodified application, fix it with CSS only, in its own commit, and say so in the report.
7. **README.** `tools/audit/README.md`: what the keyboard check does, the flag, and the limits (it does not judge the order, and it judges the indicator by computed-style difference, not by contrast: the contrast of the focus ring is a matter for axe and the design tokens).

## Acceptance criteria

From the repository root: `node --test tools/audit/testid-audit.test.mjs tools/audit/browser-audit.test.mjs tools/audit/docs-lint.test.mjs` and the new test file, `node tools/audit/testid-audit.mjs`, `node tools/audit/docs-lint.mjs`, and the browser audit in both themes (all states, 0 failures; the light run with `--catalog docs/TESTIDS.md` shows the catalog unchanged); from `frontend/`: `pnpm lint`, `pnpm typecheck`, `pnpm test:coverage`, `pnpm build` if you touched the frontend. The audit must still finish in a reasonable time (say how long a run takes before and after).

## Rules for this task

- Commit as you go, in small real steps (about 6 to 10 commits: the pure module with its tests first, then the walk, then the README). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- If a command runs more than 3 minutes, interrupt it (esc) and look for the cause; a stuck headless browser is a bug to find, not a wait.
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, the two outcomes of requirement 6, the number of Tab stops walked per theme, the run time before and after, and any deviation or open question.
