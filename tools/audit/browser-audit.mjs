#!/usr/bin/env node
// Browser audit of the test id contract and of accessibility (docs/TESTABILITY.md).
//
// It opens every state of tools/audit/states.json in a headless Chromium, logs in as the
// state's user, waits for the state to render, and reports:
//   - an interactive element without a valid data-testid (grammar read from frontend/src/lib/testid.ts);
//   - a data-testid used twice on one page;
//   - every axe-core violation of impact serious or critical (WCAG 2.0/2.1 A and AA);
//   - a document, script, stylesheet, image or font the page loads that answers 4xx or 5xx
//     (the pure check is in resources.mjs; Fetch and XHR responses are ignored, error states
//     answer 4xx on purpose);
//   - a page that declares no site icon while /favicon.ico answers 4xx or 5xx, or whose declared
//     icon answers 4xx or 5xx: the audit fetches the address a real browser loads (the pure
//     check is also in resources.mjs);
//   - a keyboard problem on a walk of real Tab presses through every audited state after it is
//     ready: an element that takes the focus and shows no visible focus indicator (WCAG 2.4.7),
//     a keyboard trap or a visible tabbable element the walk never reaches (WCAG 2.1.2); the
//     pure check is in keyboard.mjs and --no-keyboard skips the walk.
// It prints the states it covered: the 100% goal is measured over those states. Exit code 1 when anything fails.

// Needs a running application (API and web) at "baseUrl" and the frontend dependencies installed.
// A state may have "viewport": { "width": 390, "height": 844 } (a phone or a tablet), "catalog": false (left out of the catalog,
// for a state that repeats the ids of another one), and "steps": [{ "click": "<test id>", "waitFor": "<test id that must become visible>" }] to reach a state
// that needs an interaction (a dialog).
// Usage: node tools/audit/browser-audit.mjs [--base http://localhost:3000] [--only name,name] [--theme light|dark] [--catalog file.md] [--json] [--no-keyboard]
//   --catalog writes the test ids found in every state as a Markdown catalog (docs/TESTIDS.md); CI compares it with the committed copy.
//   --theme pins the explicit choice of the theme selector (the localStorage key of frontend/src/lib/theme.ts) before every
//   page loads and checks that <html data-theme> took it, so the same states can be audited in both voices of the design;
//   without it the page follows the browser default.
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { keyboardFailures, MAX_TAB_PRESSES } from "./keyboard.mjs";
import { iconFailures, resourceFailures } from "./resources.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "..", "..");
const frontend = join(repoRoot, "frontend");
const config = JSON.parse(readFileSync(join(here, "states.json"), "utf8"));
const args = process.argv.slice(2);
const option = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : undefined; };
const base = (option("--base") ?? process.env.AUDIT_BASE_URL ?? config.baseUrl).replace(/\/+$/, "");
const only = option("--only")?.split(",");
const asJson = args.includes("--json");
const catalogPath = option("--catalog");
if (args.includes("--catalog") && (!catalogPath || catalogPath.startsWith("--"))) {
  console.error("--catalog needs a file name, for example --catalog docs/TESTIDS.md");
  process.exit(2);
}
if (catalogPath && only) {
  console.error("--catalog describes every state, so it cannot be combined with --only");
  process.exit(2);
}
// --no-keyboard skips the keyboard walk (task 062): a quick run without the visible-focus
// and no-keyboard-trap check, at the cost of the guarantee.
const keyboard = !args.includes("--no-keyboard");
// --theme light|dark or --theme=light|dark; any other spelling or value stops the audit before it starts,
// so a typo can never turn into a silently unpinned run.
const themeArgs = args.filter((arg) => arg === "--theme" || arg.startsWith("--theme"));
let theme;
if (themeArgs.length > 0) {
  const arg = themeArgs[0];
  theme = arg === "--theme" ? args[args.indexOf(arg) + 1] : arg.startsWith("--theme=") ? arg.slice("--theme=".length) : undefined;
  if (themeArgs.length > 1 || (theme !== "light" && theme !== "dark")) {
    console.error(`--theme must be given once, as "--theme light" or "--theme dark" (got: ${args.filter((a, i) => a.startsWith("--theme") || args[i - 1] === "--theme").join(" ")})`);
    process.exit(2);
  }
}

const pattern = new RegExp(/export const TEST_ID_PATTERN =\s*\/(.+)\/;/.exec(readFileSync(join(frontend, "src/lib/testid.ts"), "utf8"))[1]);
const axeSource = readFileSync(join(frontend, "node_modules/axe-core/axe.min.js"), "utf8");
// The storage key of the theme selector, read from its one definition like the test id grammar above.
const themeKey = /export const THEME_STORAGE_KEY = "([^"]+)";/.exec(readFileSync(join(frontend, "src/lib/theme.ts"), "utf8"))?.[1];
if (theme && !themeKey) throw new Error("THEME_STORAGE_KEY not found in frontend/src/lib/theme.ts");

function findChrome() {
  const candidates = [process.env.CHROME_BIN, "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser"];
  const found = candidates.find((path) => path && existsSync(path));
  if (!found) throw new Error("No Chrome or Chromium found: set CHROME_BIN");
  return found;
}

const sleep = (ms) => new Promise((resolveSleep) => setTimeout(resolveSleep, ms));

async function login(email) {
  const response = await fetch(`${base}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password: config.password }),
  });
  if (!response.ok) throw new Error(`login of ${email} failed with ${response.status}`);
  const cookie = /labapp_session=([^;]+)/.exec(response.headers.get("set-cookie") ?? "");
  if (!cookie) throw new Error(`login of ${email} set no session cookie`);
  return cookie[1];
}

// Runs inside the page: interactive elements and test ids.
const PAGE_CHECK = `(() => {
  const roles = new Set(["button","link","checkbox","radio","switch","tab","menuitem","option","combobox","textbox","slider","spinbutton"]);
  const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  const inDevTools = (el) => !!el.closest("nextjs-portal, [data-nextjs-dev-tools-button], [data-next-badge-root]");
  const interactive = [...document.querySelectorAll("a[href], button, input:not([type=hidden]), select, textarea, summary, [tabindex], [role]")]
    .filter((el) => visible(el) && !inDevTools(el))
    .filter((el) => {
      if (el.matches("a[href], button, input, select, textarea, summary")) return true;
      const tabindex = el.getAttribute("tabindex");
      if (tabindex !== null && Number(tabindex) >= 0) return true;
      return roles.has(el.getAttribute("role") ?? "");
    });
  const withId = [...document.querySelectorAll("[data-testid]")].filter((el) => !inDevTools(el));
  const all = withId.map((el) => el.getAttribute("data-testid"));
  const elements = withId.map((el) => {
    const tag = el.tagName.toLowerCase();
    const type = tag === "input" ? el.type : null;
    const role = el.getAttribute("role");
    return { id: el.getAttribute("data-testid"), element: tag + (type ? "[type=" + type + "]" : "") + (role ? "[role=" + role + "]" : "") };
  });
  const duplicates = [...new Set(all.filter((id, i) => all.indexOf(id) !== i))];
  return {
    missing: interactive.filter((el) => !el.getAttribute("data-testid")).map((el) => el.outerHTML.slice(0, 120)),
    ids: all,
    elements,
    duplicates,
  };
})()`;

// Runs inside the page: the tabbable elements of the state (the keyboard
// check, task 062) with the unfocused computed-style snapshot of each. The
// walk presses the Tab key; the alert that receives the focus
// programmatically has tabindex="-1" and is not tabbable; a scrollable
// region with tabindex="0" (the project's TableScroll) is. An element
// inside a closed dialog or with inert stays out, and so does the element a
// modal dialog makes unreadable: the browser itself cannot tab into them.
// Runs inside the page: the tabbable elements of the state (the keyboard
// check, task 062) with the unfocused computed-style snapshot of each. The
// walk presses the Tab key; the alert that receives the focus
// programmatically has tabindex="-1" and is not tabbable; a scrollable
// region with tabindex="0" (the project's TableScroll) is. An element
// inside a closed dialog or with inert stays out, and so does the element a
// modal dialog makes unreadable: the browser itself cannot tab into them.
const TAB_PROPERTIES = ["outlineStyle", "outlineWidth", "outlineColor", "boxShadow", "borderTopColor", "borderTopWidth", "backgroundColor", "color", "textDecorationLine"];
const PAGE_TABBABLE = `(() => {
  const rules = "nextjs-portal, [data-nextjs-dev-tools-button], [data-next-badge-root]";
  const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  const node = (el) => {
    const testId = el.getAttribute("data-testid");
    if (testId) return testId;
    const tag = el.tagName.toLowerCase();
    const attribute = (name) => (el.getAttribute(name) ?? "").trim();
    const labelledby = attribute("aria-labelledby")
      ? attribute("aria-labelledby").split(/\\s+/).map((id) => document.getElementById(id)?.textContent ?? "").join(" ").replace(/\\s+/g, " ").trim()
      : "";
    const name = attribute("aria-label") || labelledby || attribute("title") || (el.textContent ?? "").replace(/\\s+/g, " ").trim();
    return name ? tag + " " + JSON.stringify(name.slice(0, 60)) : tag;
  };
  const style = (el) => {
    const s = getComputedStyle(el);
    return { outlineStyle: s.outlineStyle, outlineWidth: s.outlineWidth, outlineColor: s.outlineColor, boxShadow: s.boxShadow,
      borderTopColor: s.borderTopColor, borderTopWidth: s.borderTopWidth, backgroundColor: s.backgroundColor, color: s.color, textDecorationLine: s.textDecorationLine };
  };
  const tabbable = [...document.querySelectorAll("a[href], button, input:not([type=hidden]), select, textarea, summary, [contenteditable], [tabindex]:not([tabindex='-1'])")]
    .filter((el) => visible(el) && !el.closest(rules) && !el.inert
      && !(el.matches("button, input, select, textarea") && el.disabled)
      && !!(el.closest("dialog")?.open)
      && !(document.querySelector("dialog:modal") && !document.querySelector("dialog:modal").contains(el)));
  window.__labappTabbable = tabbable;
  return tabbable.map((el) => ({ label: node(el), unfocused: style(el) }));
})()`;

// Runs after a Tab press: the element the focus is on, whether it is inside
// the page's document, its visibility and its focused computed-style
// snapshot. When the focus left the page content (document.body reports the
// browser chrome) or went to a tool element, the walk is over.
const PAGE_STOP = `(() => {
  const active = document.activeElement;
  if (!(active instanceof Element) || active === document.body || active === document.documentElement) return { left: true };
  if (active.closest("nextjs-portal, [data-nextjs-dev-tools-button], [data-next-badge-root]")) return { left: true };
  const node = (el) => {
    const testId = el.getAttribute("data-testid");
    if (testId) return testId;
    const tag = el.tagName.toLowerCase();
    const attribute = (name) => (el.getAttribute(name) ?? "").trim();
    const labelledby = attribute("aria-labelledby")
      ? attribute("aria-labelledby").split(/\\s+/).map((id) => document.getElementById(id)?.textContent ?? "").join(" ").replace(/\\s+/g, " ").trim()
      : "";
    const name = attribute("aria-label") || labelledby || attribute("title") || (el.textContent ?? "").replace(/\\s+/g, " ").trim();
    return name ? tag + " " + JSON.stringify(name.slice(0, 60)) : tag;
  };
  return {
    index: window.__labappTabbable.indexOf(active),
    label: node(active),
    visible: !!(active.offsetWidth || active.offsetHeight || active.getClientRects().length),
    focused: ${JSON.stringify(TAB_PROPERTIES)}.reduce((styles, property) => ((styles[property] = getComputedStyle(active)[property]), styles), {}),
  };
})()`;
// Natural order, independent of the locale: digit runs compare as numbers, everything else by code unit.
function naturalCompare(a, b) {
  const partsA = a.match(/\d+|\D+/g) ?? [];
  const partsB = b.match(/\d+|\D+/g) ?? [];
  for (let i = 0; i < Math.min(partsA.length, partsB.length); i++) {
    const [x, y] = [partsA[i], partsB[i]];
    if (x === y) continue;
    if (/^\d/.test(x) && /^\d/.test(y)) return Number(x) - Number(y) || (x < y ? -1 : 1);
    return x < y ? -1 : 1;
  }
  return partsA.length - partsB.length;
}

// The catalog: the test ids of every state and the element that carries each. Ids present in every logged-in state
// (the app shell) are listed once. Sorted, so that two runs on the same data produce the same file.
function renderCatalog(report) {
  report = report.filter((entry) => config.states.find((state) => state.name === entry.name)?.catalog !== false);
  const loggedIn = report.filter((entry) => config.states.find((state) => state.name === entry.name)?.user);
  const shell = loggedIn.length > 1
    ? new Set(loggedIn[0].elements.map((row) => row.id).filter((id) => loggedIn.every((entry) => entry.elements.some((row) => row.id === id))))
    : new Set();
  const table = (rows) => ["| Test id | Element |", "|---|---|", ...[...rows].sort((a, b) => naturalCompare(a.id, b.id) || naturalCompare(a.element, b.element)).map((row) => `| \`${row.id}\` | \`${row.element}\` |`), ""];
  const lines = [
    "# Test id catalog",
    "",
    "Every `data-testid` found in each audited state, with the element that carries it (its tag, the type of an input and",
    "an explicit `role`, not the implicit one). It is **generated**: `node tools/audit/browser-audit.mjs --catalog docs/TESTIDS.md`",
    "against a freshly seeded application, and CI fails when the committed copy is out of date.",
    "",
    "- Elements that are not visible but carry an id are included.",
    "- A number at the end of an id is the id of a record of the seed data (`customers-list-row-3`), or a position in a list",
    "  (`auth-login-demo-item-2`).",
    "- Only the states of `tools/audit/states.json` are covered. An id that appears only after an interaction (a field error",
    "  after a failed submit, a confirmation message) is not here until a state reaches it; the grammar still applies to it",
    "  ([TESTABILITY.md](TESTABILITY.md)).",
    "- The ids of the app shell that every logged-in state has are listed once, under \"App shell\".",
    "",
  ];
  if (shell.size > 0) {
    lines.push("## App shell", "", "Present in every logged-in state.", "", ...table(loggedIn[0].elements.filter((row) => shell.has(row.id))));
  }
  for (const entry of report) {
    const state = config.states.find((candidate) => candidate.name === entry.name);
    lines.push(`## ${entry.name}`, "", `\`${entry.path}\`, ${state?.user ? `logged in as \`${state.user}\`` : "no session"}. Page title: \`${entry.title}\`.`, "", ...table(entry.elements.filter((row) => !shell.has(row.id))));
  }
  return `${lines.join("\n").replace(/\n+$/, "")}\n`;
}

async function main() {
  const profile = mkdtempSync(join(tmpdir(), "browser-audit-"));
  const port = 9400 + Math.floor(Math.random() * 400);
  const chromeFlags = [
    "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--no-first-run",
    "--no-default-browser-check", "--disable-extensions", "--hide-scrollbars",
    "--remote-debugging-address=127.0.0.1", `--remote-debugging-port=${port}`, "--remote-allow-origins=*",
    `--user-data-dir=${profile}`, "about:blank",
  ];
  const chrome = spawn(findChrome(), chromeFlags, { stdio: ["ignore", "ignore", "pipe"] });
  let chromeLog = "";
  chrome.stderr.on("data", (chunk) => { chromeLog = (chromeLog + chunk).slice(-4000); });
  let chromeExit = null;
  chrome.on("exit", (code, signal) => { chromeExit = `exit code ${code}, signal ${signal}`; });
  const cleanup = () => { chrome.kill(); try { rmSync(profile, { recursive: true, force: true }); } catch { /* ignore */ } };
  try {
    let page;
    for (let i = 0; i < 160 && !page && chromeExit === null; i++) {
      try { page = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === "page"); } catch { await sleep(250); }
    }
    if (!page) throw new Error(`Chrome did not start (${chromeExit ?? "no answer on the debugging port after 40 s"}). Chrome said:\n${chromeLog}`);
    const ws = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise((r) => (ws.onopen = r));
    let nextId = 0; const waiting = new Map();
    let responses = [];
    ws.onmessage = (event) => {
      const m = JSON.parse(event.data);
      if (m.id && waiting.has(m.id)) { waiting.get(m.id)(m); waiting.delete(m.id); }
      // Every network response of the state window: the resource check reads it (resources.mjs).
      else if (m.method === "Network.responseReceived") {
        responses.push({ type: m.params.type, status: m.params.response.status, url: m.params.response.url });
      }
    };
    const send = (method, params = {}) => new Promise((r) => { const id = ++nextId; waiting.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
    const evaluate = async (expression) => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.result.exceptionDetails) throw new Error(result.result.exceptionDetails.exception?.description ?? "evaluate failed");
      return result.result.result.value;
    };
    await send("Page.enable"); await send("Network.enable"); await send("Runtime.enable");
    if (theme) {
      await send("Page.addScriptToEvaluateOnNewDocument", { source: `try { window.localStorage.setItem(${JSON.stringify(themeKey)}, ${JSON.stringify(theme)}); } catch (error) { /* blocked storage */ }` });
    }
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });

    const cookies = new Map();
    const report = [];
    let tabStops = 0;
    for (const state of config.states) {
      if (only && !only.includes(state.name)) continue;
      await send("Network.clearBrowserCookies");
      // The window of the state: a phone or a tablet for the states that name one, the desktop otherwise.
      const viewport = state.viewport ?? { width: 1280, height: 900 };
      await send("Emulation.setDeviceMetricsOverride", { width: viewport.width, height: viewport.height, deviceScaleFactor: 1, mobile: viewport.width < 600 });
      if (state.user) {
        if (!cookies.has(state.user)) cookies.set(state.user, await login(state.user));
        await send("Network.setCookie", { name: "labapp_session", value: cookies.get(state.user), url: base, httpOnly: true });
      }
      // A blank document first, so that the poll below can never read the previous state's page.
      await send("Page.navigate", { url: "about:blank" });
      // The network window of the state: only what this state loads (about:blank makes no request).
      responses = [];
      await send("Page.navigate", { url: `${base}${state.path}` });
      const entry = { name: state.name, path: state.path, failures: [], warnings: [], ids: 0 };
      let rendered = false;
      for (let i = 0; i < 80 && !rendered; i++) {
        await sleep(250);
        rendered = await evaluate(`!!document.querySelector('[data-testid="${state.waitFor}"]')`).catch(() => false);
      }
      if (!rendered) {
        entry.failures.push(`the state never rendered the element "${state.waitFor}"`);
        report.push(entry);
        continue;
      }
      // Settled: no request is still loading (the home counters, for example, each load on their own), so the ids
      // and the axe run see the final page, and the catalog never records a loading state.
      let settled = false;
      for (let i = 0; i < 80 && !settled; i++) {
        settled = await evaluate(`!document.querySelector('[aria-busy="true"], [data-testid$="-loading-status"]')`).catch(() => false);
        if (!settled) await sleep(250);
      }
      if (!settled) {
        entry.failures.push("the state never finished loading (an element with aria-busy or a loading status stayed on the page)");
        report.push(entry);
        continue;
      }
      await sleep(300);
      // Interaction steps (a state that needs a click to reach it, a dialog for example): click the element with the
      // test id, then wait until the element named by "waitFor" is visible on the page.
      let stepFailed = false;
      for (const step of state.steps ?? []) {
        const clicked = await evaluate(`(() => { const el = document.querySelector('[data-testid="${step.click}"]'); if (!el) return false; el.click(); return true; })()`);
        if (!clicked) { entry.failures.push(`step: no element with the test id "${step.click}" to click`); stepFailed = true; break; }
        let shown = false;
        for (let i = 0; i < 40 && !shown; i++) {
          await sleep(100);
          shown = await evaluate(`(() => { const el = document.querySelector('[data-testid="${step.waitFor}"]'); return !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length); })()`).catch(() => false);
        }
        if (!shown) { entry.failures.push(`step: "${step.waitFor}" never became visible after clicking "${step.click}"`); stepFailed = true; break; }
      }
      if (stepFailed) { report.push(entry); continue; }
      if (state.steps?.length) await sleep(300);
      if (theme) {
        // The run is only worth something if the page really took the theme it was asked for.
        const applied = await evaluate(`document.documentElement.getAttribute("data-theme")`);
        if (applied !== theme) entry.failures.push(`the ${theme} theme was not applied (data-theme is ${applied === null ? "absent" : `"${applied}"`})`);
      }
      // No page may scroll sideways: the content has to fit the window it is shown in.
      const overflow = await evaluate(`({ scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth })`);
      if (overflow.scrollWidth > overflow.innerWidth + 1) entry.failures.push(`the page scrolls horizontally (${overflow.scrollWidth}px of content in a ${overflow.innerWidth}px window)`);
      entry.title = await evaluate("document.title");
      if (state.title !== undefined && entry.title !== state.title) entry.failures.push(`the page title is "${entry.title}", expected "${state.title}"`);
      const check = await evaluate(PAGE_CHECK);
      entry.ids = check.ids.length;
      entry.elements = check.elements;
      for (const html of check.missing) entry.failures.push(`interactive element without a test id: ${html}`);
      for (const id of check.duplicates) entry.failures.push(`test id used more than once on the page: ${id}`);
      for (const id of new Set(check.ids)) if (!pattern.test(id)) entry.failures.push(`test id does not match the grammar: ${id}`);
      for (const failure of resourceFailures(state, responses)) entry.failures.push(failure);
      // The site icon (task 047), probed as a real browser would: load the icon the page
      // declares, or /favicon.ico when it declares none (headless Chrome makes no favicon
      // request of its own and classifies the declared one as an untracked Other response,
      // both measured, so the audit makes the browser's request itself and checks one answer).
      const iconHref = await evaluate('document.querySelector("link[rel~=icon]")?.getAttribute("href") ?? null');
      const iconProbe = new URL(iconHref ?? "/favicon.ico", `${base}/`);
      const iconStatus = (await fetch(iconProbe)).status;
      for (const failure of iconFailures({ declared: iconHref !== null, href: iconProbe.href }, iconStatus)) entry.failures.push(failure);
      await evaluate(axeSource);
      const axe = await evaluate(`axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] } }).then((r) => r.violations.map((v) => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.slice(0, 4).map((n) => n.target.join(" ") + " :: " + (n.failureSummary || "").split("\\n").slice(0, 2).join(" ").slice(0, 160)) })))`);
      for (const v of axe) {
        const text = `axe ${v.id} (${v.impact}): ${v.help} -> ${v.nodes.join(" | ")}`;
        (v.impact === "serious" || v.impact === "critical" ? entry.failures : entry.warnings).push(text);
      }
      // The keyboard walk (task 062): real Tab keystrokes through the DevTools Input
      // domain, never a programmatic .focus(). First the unfocused snapshot of every
      // tabbable element in one pass, then the presses: up to MAX_TAB_PRESSES, or
      // until the focus leaves the page content or returns to the first element of
      // the walk. The stops are judged by keyboard.mjs: a visible focus indicator
      // (WCAG 2.4.7), no trap (WCAG 2.1.2) and every visible tabbable element reached.
      if (keyboard) {
        const tabbable = await evaluate(PAGE_TABBABLE);
        let presses = 0;
        let leftContent = false;
        const stops = [];
        // The element that owns the focus when the walk starts (the "Volver"
        // button of a confirmation dialog, given it by showModal) is reached
        // at the start: it is the first stop, before any press. An element
        // that is not tabbable (the alert that receives the focus
        // programmatically) is not part of the walk.
        const opening = await evaluate(PAGE_STOP);
        if (!opening.left) stops.push({ ...opening, tab: false });
        while (presses < MAX_TAB_PRESSES) {
          presses++;
          await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9, nativeVirtualKeyCode: 9 });
          await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9, nativeVirtualKeyCode: 9 });
          const stop = await evaluate(PAGE_STOP);
          if (stop.left) { leftContent = true; break; }
          stops.push({ ...stop, tab: true });
          const key = (s) => (typeof s.index === "number" ? s.index : s.label);
          const stuck = key(stops.at(-1));
          // A trap cannot repair itself: five presses on the same element are enough to say so.
          if (stops.length >= 5 && stops.slice(-4).every((s) => key(s) === stuck)) break;
          // The cycle is over when the focus is back on the first element of the walk.
          if (stops.length > 1 && key(stops.at(-1)) === key(stops[0])) break;
        }
        entry.tabStops = stops.length;
        tabStops += stops.length;
        for (const failure of keyboardFailures({ tabbable, stops, presses, leftContent })) entry.failures.push(failure);
      }
      report.push(entry);
    }
    ws.close();
    return { report, tabStops };
  } finally {
    cleanup();
  }
  return tabStops;
}

const { report, tabStops } = await main();
if (catalogPath) {
  const incomplete = report.filter((entry) => !entry.elements);
  if (incomplete.length > 0) {
    console.error(`Not writing ${catalogPath}: ${incomplete.length} state(s) did not render (${incomplete.map((entry) => entry.name).join(", ")}).`);
  } else {
    writeFileSync(catalogPath, renderCatalog(report));
  }
}
if (asJson) console.log(JSON.stringify(report.map(({ elements, ...entry }) => entry), null, 2));
let failed = 0;
for (const entry of report) {
  const status = entry.failures.length ? "FAIL" : "ok  ";
  if (!asJson) console.log(`${status} ${entry.name.padEnd(28)} ${entry.path.padEnd(22)} ${entry.ids} test ids${entry.warnings.length ? `, ${entry.warnings.length} warning(s)` : ""}`);
  if (!asJson) for (const f of entry.failures) console.log(`       - ${f}`);
  if (!asJson) for (const w of entry.warnings) console.log(`       ~ ${w}`);
  failed += entry.failures.length;
}
console.log(`Browser audit${theme ? ` (${theme} theme)` : ""}: ${report.length} state(s) covered, ${failed} failure(s)${keyboard ? `, ${tabStops} Tab stops walked` : ", without the keyboard check (--no-keyboard)"}.`);
process.exit(failed === 0 ? 0 : 1);
