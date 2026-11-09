#!/usr/bin/env node
// Online smoke test (task 069): one command that checks that a deployment of
// the demo — the Vercel project, a preview or the local stack — answers as
// docs/DEPLOYMENT.md, docs/SPEC.md and docs/AUTOMATION_GUIDE.md say. It runs
// the checks in order, prints one line per check and exits 1 when any check
// failed. Node's own fetch and node:test are the only dependencies.
//
//   node tools/smoke/online-smoke.mjs --base https://example.vercel.app \
//     [--token <test token>] [--json] [--allow-reset]
//
// The token may also come from TEST_TOKEN. It is never printed.

import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  SESSION_COOKIE,
  demoPassword,
  firstCsvLine,
  headerFailures,
  problemFailures,
  retryingFetch,
  sessionCookie,
} from "./checks.mjs";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const REQUEST_TIMEOUT_MS = 10_000;
const TOTAL_TIMEOUT_MS = 180_000;
const HEALTH_ATTEMPTS = 5;
const HEALTH_DELAY_MS = 5_000;
const CUSTOMERS_CSV_HEADER =
  "id,name,email,phone,tax_id,address,status,created_at,updated_at";
const REQUIRED_PATHS = [
  "/api/customers",
  "/api/orders",
  "/api/invoices",
  "/api/customers/import",
];
const USERS = [
  { email: "admin@labapp.test", role: "admin" },
  { email: "sales@labapp.test", role: "sales" },
  { email: "finance@labapp.test", role: "finance" },
  { email: "readonly@labapp.test", role: "readonly" },
];

const USAGE = `Usage: node tools/smoke/online-smoke.mjs --base <url> [options]

Checks a deployment of the LabApp demo. Options:
  --base <url>        The base URL (required): a deployment, a preview or the local web app.
  --token <token>     The test token of the /__test__ controls (or set TEST_TOKEN).
  --json              Print the report as one JSON document instead of one line per check.
  --allow-reset       Call the test controls' reset and create one customer, then deactivate it.
  -h, --help           Show this help.

Exit codes: 0 every check passed, 1 a check failed, 2 the command line is invalid.`;

function parseArgs(argv) {
  const options = {
    base: null,
    token: process.env.TEST_TOKEN || null,
    json: false,
    allowReset: false,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--base" || argument.startsWith("--base=")) {
      const value = argument.includes("=")
        ? argument.slice("--base=".length)
        : argv[++index];
      if (value === undefined) {
        throw new Error("--base needs a value");
      }
      options.base = value;
    } else if (argument === "--token" || argument.startsWith("--token=")) {
      const value = argument.includes("=")
        ? argument.slice("--token=".length)
        : argv[++index];
      if (value === undefined) {
        throw new Error("--token needs a value");
      }
      options.token = value;
    } else if (argument === "--json") {
      options.json = true;
    } else if (argument === "--allow-reset") {
      options.allowReset = true;
    } else if (argument === "--help" || argument === "-h") {
      options.help = true;
    } else {
      throw new Error(`unknown argument: ${argument}`);
    }
  }
  return options;
}

function normalizeBase(raw) {
  if (!raw) {
    throw new Error("--base is required");
  }
  let url;
  try {
    url = new URL(raw);
  } catch {
    throw new Error(`--base is not a URL: ${raw}`);
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error(`--base must start with http:// or https://: ${raw}`);
  }
  if (url.username || url.password) {
    throw new Error("--base must not carry credentials");
  }
  if (url.search || url.hash) {
    throw new Error("--base must not carry a query or a fragment");
  }
  return `${url.origin}${url.pathname.replace(/\/+$/, "")}`;
}

function isLocalBase(base) {
  const hostname = new URL(base).hostname.toLowerCase();
  return (
    hostname === "localhost" ||
    hostname === "127.0.0.1" ||
    hostname === "[::1]" ||
    hostname === "::1"
  );
}

const pass = (detail) => ({ status: "ok", detail });
const fail = (detail) => ({ status: "FAIL", detail });
const skip = (detail) => ({ status: "skipped", detail });
const warn = (detail) => ({ status: "warning", detail });
const info = (detail) => ({ status: "info", detail });

function expectType(response, prefix) {
  const type = response.headers.get("content-type") ?? "";
  if (!type.toLowerCase().startsWith(prefix.toLowerCase())) {
    return `GET ${response.url} answered "${type || "(no content type)"}", expected a ${prefix} answer`;
  }
  return null;
}

function titleOf(html) {
  const match = /<title>([^<]*)<\/title>/i.exec(html);
  return match ? match[1].trim() : null;
}

function withCookie(cookie, init = {}) {
  return {
    ...init,
    headers: {
      ...(init.headers ?? {}),
      Cookie: `${SESSION_COOKIE}=${cookie}`,
    },
  };
}

async function readJson(response) {
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(
      `${response.url} answered ${response.status} with a body that is not JSON`,
    );
  }
}

function readDemoPassword() {
  const path = resolve(REPO_ROOT, "docs", "SEED.md");
  let text;
  try {
    text = readFileSync(path, "utf8");
  } catch {
    throw new Error(`cannot read the demo password from ${path}`);
  }
  const password = demoPassword(text);
  if (!password) {
    throw new Error(`the demo password was not found in ${path}`);
  }
  return password;
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    console.log(USAGE);
    return 0;
  }
  const base = normalizeBase(options.base);
  const local = isLocalBase(base);
  const secure = new URL(base).protocol === "https:";
  const password = readDemoPassword();
  const deadline = Date.now() + TOTAL_TIMEOUT_MS;

  const results = [];
  const state = {
    apiUp: null,
    cookies: new Map(),
    customersTotal: null,
    resetTotal: null,
    resetDone: false,
    createdId: null,
    uniqueName: `Smoke ${Date.now()}`,
    uniqueEmail: `smoke-${Date.now()}@example.test`,
  };

  function record(status, name, detail) {
    const entry = { status, name };
    if (detail) {
      entry.detail = detail;
    }
    results.push(entry);
    if (!options.json) {
      console.log(
        `${status === "FAIL" ? "FAIL" : status.padEnd(7)} ${name}${
          detail ? ` (${detail})` : ""
        }`,
      );
    }
  }

  async function run(name, check) {
    if (Date.now() >= deadline) {
      const detail = "the total timeout of 3 minutes was reached";
      record("FAIL", name, detail);
      return fail(detail);
    }
    try {
      const outcome = (await check()) ?? pass();
      record(outcome.status, name, outcome.detail);
      return outcome;
    } catch (error) {
      const detail = error instanceof Error ? error.message : String(error);
      record("FAIL", name, detail);
      return fail(detail);
    }
  }

  async function fetchUrl(url, init = {}) {
    const remaining = deadline - Date.now();
    if (remaining <= 0) {
      throw new Error("the total timeout of 3 minutes was reached");
    }
    return fetch(url, {
      ...init,
      redirect: "follow",
      signal: AbortSignal.timeout(Math.min(REQUEST_TIMEOUT_MS, remaining)),
    });
  }

  function fetchPath(path, init = {}) {
    return fetchUrl(`${base}${path}`, init);
  }

  function login(email, loginPassword, extraHeaders = {}) {
    return fetchPath("/api/auth/login", {
      method: "POST",
      headers: { "content-type": "application/json", ...extraHeaders },
      body: JSON.stringify({ email, password: loginPassword }),
    });
  }

  function apiGuard() {
    if (state.apiUp === true) {
      return null;
    }
    return skip("GET /api/health did not answer 200, so the API is not usable");
  }

  function salesCookie() {
    return state.cookies.get("sales@labapp.test") ?? null;
  }

  function salesGuard() {
    const guard = apiGuard();
    if (guard) {
      return guard;
    }
    if (!salesCookie()) {
      return skip("the login of sales@labapp.test failed");
    }
    return null;
  }

  if (!options.json) {
    console.log(`Online smoke test: ${base}${local ? " (local stack)" : ""}`);
  }

  // Web pages.
  await run("web: GET /", async () => {
    const response = await fetchPath("/");
    if (response.status !== 200) {
      return fail(`GET ${response.url} answered ${response.status}, expected 200`);
    }
    const typeFailure = expectType(response, "text/html");
    return typeFailure ? fail(typeFailure) : pass();
  });

  await run("web: GET /login", async () => {
    const response = await fetchPath("/login");
    if (response.status !== 200) {
      return fail(`GET ${response.url} answered ${response.status}, expected 200`);
    }
    const typeFailure = expectType(response, "text/html");
    if (typeFailure) {
      return fail(typeFailure);
    }
    const title = titleOf(await response.text());
    if (title !== "Iniciar sesión · LabApp") {
      return fail(
        `GET ${response.url} has the title ${JSON.stringify(title)}, expected "Iniciar sesión · LabApp"`,
      );
    }
    return pass();
  });

  await run("web: security headers", async () => {
    const response = await fetchPath("/login");
    const failures = headerFailures(response.headers, [
      { name: "x-content-type-options", equals: "nosniff" },
      { name: "x-frame-options", equals: "DENY" },
    ]);
    return failures.length
      ? fail(`GET ${response.url}: ${failures.join("; ")}`)
      : pass();
  });

  await run("web: Content-Security-Policy", async () => {
    if (local) {
      return skip(
        "the base is local, where Next.js sends no Content-Security-Policy (production only)",
      );
    }
    const response = await fetchPath("/login");
    const policy = response.headers.get("content-security-policy");
    if (!policy) {
      return fail(
        `GET ${response.url} has no Content-Security-Policy header, expected one in production`,
      );
    }
    if (!policy.includes("default-src 'self'")) {
      return fail(
        `GET ${response.url} has the policy "${policy}", expected it to contain "default-src 'self'"`,
      );
    }
    return pass();
  });

  await run("web: GET /no-such-page", async () => {
    const response = await fetchPath("/no-such-page");
    if (response.status !== 404) {
      return fail(`GET ${response.url} answered ${response.status}, expected 404`);
    }
    const typeFailure = expectType(response, "text/html");
    if (typeFailure) {
      return fail(typeFailure);
    }
    const title = titleOf(await response.text());
    if (title !== "Página no encontrada · LabApp") {
      return fail(
        `GET ${response.url} has the title ${JSON.stringify(title)}, expected "Página no encontrada · LabApp"`,
      );
    }
    return pass();
  });

  await run("web: GET /icon.svg", async () => {
    const response = await fetchPath("/icon.svg");
    if (response.status !== 200) {
      return fail(`GET ${response.url} answered ${response.status}, expected 200`);
    }
    const typeFailure = expectType(response, "image/");
    return typeFailure ? fail(typeFailure) : pass();
  });

  // API basics.
  await run("api: GET /api/health", async () => {
    const url = `${base}/api/health`;
    try {
      const result = await retryingFetch(url, {}, {
        attempts: HEALTH_ATTEMPTS,
        delayMs: HEALTH_DELAY_MS,
        fetchImpl: (target, init) => fetchUrl(target, init),
        sleep: (milliseconds) =>
          new Promise((resolveSleep) =>
            setTimeout(
              resolveSleep,
              Math.max(0, Math.min(milliseconds, deadline - Date.now())),
            ),
          ),
      });
      state.apiUp = result.response.status === 200;
      if (!state.apiUp) {
        return fail(
          `GET ${result.response.url} answered ${result.response.status}, expected 200 (after ${result.attempts} attempts, ${HEALTH_DELAY_MS / 1000} s apart)`,
        );
      }
      return pass(
        result.attempts > 1
          ? `answered 200 on attempt ${result.attempts}`
          : undefined,
      );
    } catch (error) {
      state.apiUp = false;
      return fail(
        `GET ${url} failed: ${error instanceof Error ? error.message : String(error)}`,
      );
    }
  });

  await run("api: GET /api/openapi.json", async () => {
    const guard = apiGuard();
    if (guard) {
      return guard;
    }
    const response = await fetchPath("/api/openapi.json");
    if (response.status !== 200) {
      return fail(`GET ${response.url} answered ${response.status}, expected 200`);
    }
    const failures = [
      ...headerFailures(response.headers, [
        { name: "x-content-type-options", equals: "nosniff" },
        { name: "cache-control", absent: true },
      ]),
    ];
    const typeFailure = expectType(response, "application/json");
    if (typeFailure) {
      failures.push(typeFailure);
    }
    const document = await readJson(response);
    if (typeof document.openapi !== "string") {
      failures.push("the contract has no openapi version");
    }
    if (
      document.paths === null ||
      typeof document.paths !== "object" ||
      Array.isArray(document.paths)
    ) {
      failures.push("the contract has no paths object");
    } else {
      const missing = REQUIRED_PATHS.filter(
        (path) => !(path in document.paths),
      );
      if (missing.length) {
        failures.push(`the contract has no paths ${missing.join(", ")}`);
      }
    }
    return failures.length
      ? fail(`${response.url}: ${failures.join("; ")}`)
      : pass();
  });

  await run("api: GET /api/docs", async () => {
    const guard = apiGuard();
    if (guard) {
      return guard;
    }
    const response = await fetchPath("/api/docs");
    if (response.status !== 200) {
      return fail(`GET ${response.url} answered ${response.status}, expected 200`);
    }
    const failures = headerFailures(response.headers, [
      { name: "x-content-type-options", equals: "nosniff" },
      { name: "cache-control", absent: true },
    ]);
    const typeFailure = expectType(response, "text/html");
    if (typeFailure) {
      failures.push(typeFailure);
    }
    return failures.length
      ? fail(`${response.url}: ${failures.join("; ")}`)
      : pass();
  });

  await run("api: unauthenticated read", async () => {
    const guard = apiGuard();
    if (guard) {
      return guard;
    }
    const response = await fetchPath("/api/customers");
    const body = await response.text();
    const failures = [];
    if (response.status !== 401) {
      failures.push(
        `GET ${response.url} answered ${response.status}, expected 401`,
      );
    }
    failures.push(
      ...problemFailures(body, {
        contentType: response.headers.get("content-type") ?? "",
        status: 401,
        code: "UNAUTHENTICATED",
      }),
    );
    failures.push(
      ...headerFailures(response.headers, [
        { name: "x-content-type-options", equals: "nosniff" },
        { name: "cache-control", equals: "no-store" },
      ]),
    );
    return failures.length
      ? fail(`${response.url}: ${failures.join("; ")}`)
      : pass();
  });

  await run("api: unknown path", async () => {
    const guard = apiGuard();
    if (guard) {
      return guard;
    }
    const response = await fetchPath("/api/nope");
    const body = await response.text();
    const failures = [];
    if (response.status !== 404) {
      failures.push(
        `GET ${response.url} answered ${response.status}, expected 404`,
      );
    }
    failures.push(
      ...problemFailures(body, {
        contentType: response.headers.get("content-type") ?? "",
        status: 404,
        code: "NOT_FOUND",
      }),
    );
    failures.push(
      ...headerFailures(response.headers, [
        { name: "x-content-type-options", equals: "nosniff" },
        { name: "cache-control", equals: "no-store" },
      ]),
    );
    return failures.length
      ? fail(`${response.url}: ${failures.join("; ")}`)
      : pass();
  });

  // The four demo users.
  for (const user of USERS) {
    await run(`users: login ${user.email}`, async () => {
      const guard = apiGuard();
      if (guard) {
        return guard;
      }
      const response = await login(user.email, password);
      if (response.status !== 200) {
        return fail(
          `POST ${response.url} answered ${response.status}, expected 200`,
        );
      }
      const body = await readJson(response);
      if (body.role !== user.role) {
        return fail(
          `POST ${response.url} returned the role ${JSON.stringify(body.role)}, expected "${user.role}"`,
        );
      }
      const cookie = sessionCookie(response.headers.getSetCookie(), { secure });
      if (cookie.failures.length) {
        return fail(`POST ${response.url}: ${cookie.failures.join("; ")}`);
      }
      state.cookies.set(user.email, cookie.value);
      return pass();
    });

    await run(`users: session of ${user.email}`, async () => {
      const guard = apiGuard();
      if (guard) {
        return guard;
      }
      const cookie = state.cookies.get(user.email);
      if (!cookie) {
        return skip(`the login of ${user.email} failed`);
      }
      const response = await fetchPath(
        "/api/auth/me",
        withCookie(cookie),
      );
      if (response.status !== 200) {
        return fail(
          `GET ${response.url} answered ${response.status}, expected 200`,
        );
      }
      const body = await readJson(response);
      if (body.email !== user.email || body.role !== user.role) {
        return fail(
          `GET ${response.url} returned ${JSON.stringify({ email: body.email, role: body.role })}, expected ${JSON.stringify({ email: user.email, role: user.role })}`,
        );
      }
      return pass();
    });
  }

  await run("users: wrong password", async () => {
    const guard = apiGuard();
    if (guard) {
      return guard;
    }
    const response = await login(
      "sales@labapp.test",
      "definitely-not-the-demo-password",
    );
    const body = await response.text();
    const failures = [];
    if (response.status !== 401) {
      failures.push(
        `POST ${response.url} answered ${response.status}, expected 401`,
      );
    }
    failures.push(
      ...problemFailures(body, {
        contentType: response.headers.get("content-type") ?? "",
        status: 401,
        code: "INVALID_CREDENTIALS",
      }),
    );
    return failures.length
      ? fail(`${response.url}: ${failures.join("; ")}`)
      : pass();
  });

  await run("users: logout ends the session", async () => {
    const guard = apiGuard();
    if (guard) {
      return guard;
    }
    const start = await login("admin@labapp.test", password);
    if (start.status !== 200) {
      return fail(
        `POST ${start.url} answered ${start.status}, expected 200`,
      );
    }
    const cookie = sessionCookie(start.headers.getSetCookie(), { secure });
    if (!cookie.value) {
      return skip(cookie.failures.join("; "));
    }
    const logout = await fetchPath(
      "/api/auth/logout",
      withCookie(cookie.value, { method: "POST" }),
    );
    if (logout.status !== 204) {
      return fail(
        `POST ${logout.url} answered ${logout.status}, expected 204`,
      );
    }
    const me = await fetchPath(
      "/api/auth/me",
      withCookie(cookie.value),
    );
    if (me.status !== 401) {
      return fail(
        `GET ${me.url} with the ended cookie answered ${me.status}, expected 401`,
      );
    }
    return pass();
  });

  // Reads through the web origin, as Sales.
  await run("reads: customers list", async () => {
    const guard = salesGuard();
    if (guard) {
      return guard;
    }
    const response = await fetchPath(
      "/api/customers",
      withCookie(salesCookie()),
    );
    if (response.status !== 200) {
      return fail(`GET ${response.url} answered ${response.status}, expected 200`);
    }
    const body = await readJson(response);
    if (!Array.isArray(body.items) || typeof body.total !== "number") {
      return fail(
        `GET ${response.url} returned ${JSON.stringify(body).slice(0, 120)}, expected an object with items and total`,
      );
    }
    state.customersTotal = body.total;
    return pass();
  });

  await run("reads: products", async () => {
    const guard = salesGuard();
    if (guard) {
      return guard;
    }
    const response = await fetchPath(
      "/api/products",
      withCookie(salesCookie()),
    );
    if (response.status !== 200) {
      return fail(`GET ${response.url} answered ${response.status}, expected 200`);
    }
    const body = await readJson(response);
    if (!Array.isArray(body.items)) {
      return fail(`GET ${response.url} returned no items array`);
    }
    if (body.items.length !== 15) {
      return warn(
        `GET ${response.url} listed ${body.items.length} products, expected 15 on a freshly seeded demo (the shared demo changes during the day)`,
      );
    }
    return pass();
  });

  await run("reads: customers export", async () => {
    const guard = salesGuard();
    if (guard) {
      return guard;
    }
    const response = await fetchPath(
      "/api/customers/export",
      withCookie(salesCookie()),
    );
    if (response.status !== 200) {
      return fail(`GET ${response.url} answered ${response.status}, expected 200`);
    }
    const failures = [];
    const typeFailure = expectType(response, "text/csv");
    if (typeFailure) {
      failures.push(typeFailure);
    }
    failures.push(
      ...headerFailures(response.headers, [
        {
          name: "content-disposition",
          matches: /^attachment;\s*filename="customers-\d{8}\.csv"/i,
        },
      ]),
    );
    const line = firstCsvLine(await response.text());
    if (line !== CUSTOMERS_CSV_HEADER) {
      failures.push(
        `the file starts with "${line}", expected "${CUSTOMERS_CSV_HEADER}"`,
      );
    }
    return failures.length
      ? fail(`${response.url}: ${failures.join("; ")}`)
      : pass();
  });

  await run("reads: sorted customers", async () => {
    const guard = salesGuard();
    if (guard) {
      return guard;
    }
    const response = await fetchPath(
      "/api/customers?sort=name&direction=asc",
      withCookie(salesCookie()),
    );
    return response.status === 200
      ? pass()
      : fail(`GET ${response.url} answered ${response.status}, expected 200`);
  });

  await run("reads: invalid sort", async () => {
    const guard = salesGuard();
    if (guard) {
      return guard;
    }
    const response = await fetchPath(
      "/api/customers?sort=bogus",
      withCookie(salesCookie()),
    );
    const body = await response.text();
    const failures = [];
    if (response.status !== 422) {
      failures.push(
        `GET ${response.url} answered ${response.status}, expected 422`,
      );
    }
    failures.push(
      ...problemFailures(body, {
        contentType: response.headers.get("content-type") ?? "",
        status: 422,
        code: "VALIDATION_ERROR",
      }),
    );
    return failures.length
      ? fail(`${response.url}: ${failures.join("; ")}`)
      : pass();
  });

  // The origin rule.
  await run("origin: wrong Origin is rejected", async () => {
    const guard = apiGuard();
    if (guard) {
      return guard;
    }
    const response = await fetchPath("/api/auth/logout", {
      method: "POST",
      headers: { Origin: "https://evil.example" },
    });
    const body = await response.text();
    const failures = [];
    if (response.status !== 403) {
      failures.push(
        `POST ${response.url} answered ${response.status}, expected 403`,
      );
    }
    failures.push(
      ...problemFailures(body, {
        contentType: response.headers.get("content-type") ?? "",
        status: 403,
        code: "CSRF_ORIGIN_MISMATCH",
      }),
    );
    return failures.length
      ? fail(`${response.url}: ${failures.join("; ")}`)
      : pass();
  });

  await run("origin: no Origin is allowed", async () => {
    const guard = apiGuard();
    if (guard) {
      return guard;
    }
    const response = await fetchPath("/api/auth/logout", { method: "POST" });
    return response.status === 204
      ? pass()
      : fail(`POST ${response.url} answered ${response.status}, expected 204`);
  });

  // The test controls stay closed without the token.
  await run("controls: reset without a token", async () => {
    const guard = apiGuard();
    if (guard) {
      return guard;
    }
    const response = await fetchPath("/__test__/reset", { method: "POST" });
    if (local && response.status === 200) {
      return info(
        "the local stack runs with TEST_MODE=1: the controls answer without a token and the data was reset",
      );
    }
    if (response.status !== 404) {
      return fail(
        `POST ${response.url} answered ${response.status} without a token, expected 404 (TEST_MODE must be 0 online)`,
      );
    }
    const failures = headerFailures(response.headers, [
      { name: "x-content-type-options", equals: "nosniff" },
    ]);
    return failures.length
      ? fail(`${response.url}: ${failures.join("; ")}`)
      : pass();
  });

  await run("controls: reset with a wrong token", async () => {
    const guard = apiGuard();
    if (guard) {
      return guard;
    }
    const response = await fetchPath("/__test__/reset", {
      method: "POST",
      headers: { "X-Test-Token": "smoke-test-wrong-token" },
    });
    if (local && response.status === 200) {
      return info(
        "the local stack runs with TEST_MODE=1: it accepts any token, so the wrong token was accepted too",
      );
    }
    if (response.status !== 404) {
      return fail(
        `POST ${response.url} answered ${response.status} with a wrong token, expected 404`,
      );
    }
    return pass();
  });

  await run("controls: clock with the test token", async () => {
    const guard = apiGuard();
    if (guard) {
      return guard;
    }
    if (!options.token) {
      return skip(
        "no test token was given (--token or TEST_TOKEN), so the open control is not called",
      );
    }
    const response = await fetchPath("/__test__/clock", {
      headers: { "X-Test-Token": options.token },
    });
    if (response.status !== 200) {
      return fail(
        `GET ${response.url} answered ${response.status} with the test token, expected 200`,
      );
    }
    const body = await readJson(response);
    if (typeof body.now !== "string" || typeof body.offset_seconds !== "number") {
      return fail(
        `GET ${response.url} returned ${JSON.stringify(body).slice(0, 120)}, expected now and offset_seconds`,
      );
    }
    return pass();
  });

  // The reset and the write need --allow-reset: they change the shared data.
  await run("reset: POST /__test__/reset", async () => {
    if (!options.allowReset) {
      return skip("--allow-reset was not given and a reset changes the shared data");
    }
    const guard = apiGuard();
    if (guard) {
      return guard;
    }
    const headers = options.token ? { "X-Test-Token": options.token } : {};
    const response = await fetchPath("/__test__/reset", {
      method: "POST",
      headers,
    });
    if (response.status !== 200) {
      return fail(`POST ${response.url} answered ${response.status}, expected 200`);
    }
    state.resetDone = true;
    return pass();
  });

  await run("reset: the customer list holds 10 customers", async () => {
    if (!options.allowReset) {
      return skip("--allow-reset was not given and a reset changes the shared data");
    }
    if (!state.resetDone) {
      return skip("the reset did not answer 200");
    }
    const guard = salesGuard();
    if (guard) {
      return guard;
    }
    const response = await fetchPath(
      "/api/customers",
      withCookie(salesCookie()),
    );
    if (response.status !== 200) {
      return fail(`GET ${response.url} answered ${response.status}, expected 200`);
    }
    const body = await readJson(response);
    state.resetTotal = body.total;
    if (body.total !== 10) {
      return fail(
        `GET ${response.url} reported total ${body.total}, expected 10 after the reset`,
      );
    }
    return pass();
  });

  await run("write: create a customer", async () => {
    if (!options.allowReset) {
      return skip("--allow-reset was not given and a write changes the shared data");
    }
    if (!state.resetDone) {
      return skip("the reset did not answer 200");
    }
    const guard = salesGuard();
    if (guard) {
      return guard;
    }
    const response = await fetchPath(
      "/api/customers",
      withCookie(salesCookie(), {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          name: state.uniqueName,
          email: state.uniqueEmail,
        }),
      }),
    );
    if (response.status !== 201) {
      return fail(`POST ${response.url} answered ${response.status}, expected 201`);
    }
    const body = await readJson(response);
    if (typeof body.id !== "number") {
      return fail(`POST ${response.url} returned no customer id`);
    }
    state.createdId = body.id;
    const location = response.headers.get("location");
    if (location !== `/api/customers/${body.id}`) {
      return fail(
        `POST ${response.url} sent Location "${location}", expected "/api/customers/${body.id}"`,
      );
    }
    return pass();
  });

  await run("write: read the customer back", async () => {
    if (!state.createdId) {
      return skip("the customer was not created");
    }
    const guard = salesGuard();
    if (guard) {
      return guard;
    }
    const response = await fetchPath(
      `/api/customers/${state.createdId}`,
      withCookie(salesCookie()),
    );
    if (response.status !== 200) {
      return fail(`GET ${response.url} answered ${response.status}, expected 200`);
    }
    const body = await readJson(response);
    if (body.name !== state.uniqueName) {
      return fail(
        `GET ${response.url} returned the name ${JSON.stringify(body.name)}, expected ${JSON.stringify(state.uniqueName)}`,
      );
    }
    return pass();
  });

  await run("write: deactivate the customer", async () => {
    if (!state.createdId) {
      return skip("the customer was not created");
    }
    const guard = salesGuard();
    if (guard) {
      return guard;
    }
    const response = await fetchPath(
      `/api/customers/${state.createdId}/deactivate`,
      withCookie(salesCookie(), { method: "POST" }),
    );
    if (response.status !== 200) {
      return fail(`POST ${response.url} answered ${response.status}, expected 200`);
    }
    const body = await readJson(response);
    if (body.status !== "inactive") {
      return fail(
        `POST ${response.url} returned the status ${JSON.stringify(body.status)}, expected "inactive"`,
      );
    }
    return pass();
  });

  await run("write: the list grew by one", async () => {
    if (!state.createdId || state.resetTotal === null) {
      return skip("the customer was not created or the list after the reset was not read");
    }
    const guard = salesGuard();
    if (guard) {
      return guard;
    }
    const response = await fetchPath(
      "/api/customers",
      withCookie(salesCookie()),
    );
    if (response.status !== 200) {
      return fail(`GET ${response.url} answered ${response.status}, expected 200`);
    }
    const body = await readJson(response);
    const expected = state.resetTotal + 1;
    if (body.total !== expected) {
      return fail(
        `GET ${response.url} reported total ${body.total}, expected ${expected}`,
      );
    }
    return pass();
  });

  const summary = {
    ok: results.filter((entry) => entry.status === "ok").length,
    warning: results.filter((entry) => entry.status === "warning").length,
    failed: results.filter((entry) => entry.status === "FAIL").length,
    skipped: results.filter((entry) => entry.status === "skipped").length,
    info: results.filter((entry) => entry.status === "info").length,
  };

  if (options.json) {
    console.log(
      JSON.stringify(
        { base, local, checks: results, summary },
        null,
        2,
      ),
    );
  } else {
    const warnings = summary.warning === 1 ? "warning" : "warnings";
    console.log(
      `\nSummary: ${summary.ok} ok, ${summary.warning} ${warnings}, ${summary.failed} failed, ${summary.skipped} skipped, ${summary.info} info`,
    );
  }
  return summary.failed > 0 ? 1 : 0;
}

main()
  .then((code) => {
    process.exitCode = code;
  })
  .catch((error) => {
    console.error(`online-smoke: ${error instanceof Error ? error.message : error}`);
    console.error(USAGE);
    process.exitCode = 2;
  });
