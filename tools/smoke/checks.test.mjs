// Tests of the pure helpers of the online smoke test (task 069), without a
// network: each helper is called with a good answer and with a bad one.
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  demoPassword,
  firstCsvLine,
  headerFailures,
  problemFailures,
  retryingFetch,
  sessionCookie,
} from "./checks.mjs";

const headers = (values) => new Headers(values);

test("header expectations: a good answer has no failure", () => {
  const failures = headerFailures(
    headers({
      "x-content-type-options": "nosniff",
      "x-frame-options": "DENY",
      "content-type": "application/problem+json",
    }),
    [
      { name: "x-content-type-options", equals: "nosniff" },
      { name: "x-frame-options", equals: "DENY" },
      { name: "content-type", matches: /^application\/problem\+json/ },
      { name: "cache-control", absent: true },
    ],
  );
  assert.deepEqual(failures, []);
});

test("header expectations: a missing header names what was expected", () => {
  const failures = headerFailures(headers({}), [
    { name: "x-frame-options", equals: "DENY" },
  ]);
  assert.deepEqual(failures, [
    'header "x-frame-options" is missing, expected "DENY"',
  ]);
});

test("header expectations: a wrong value shows the expected and the actual", () => {
  const failures = headerFailures(headers({ "x-frame-options": "SAMEORIGIN" }), [
    { name: "x-frame-options", equals: "DENY" },
  ]);
  assert.deepEqual(failures, [
    'header "x-frame-options" was "SAMEORIGIN", expected "DENY"',
  ]);
});

test("header expectations: a header that must be absent", () => {
  const failures = headerFailures(headers({ "cache-control": "public" }), [
    { name: "cache-control", absent: true },
  ]);
  assert.deepEqual(failures, [
    'header "cache-control" was "public", expected no header',
  ]);
});

test("header expectations: a case-insensitive lookup on a plain object", () => {
  assert.deepEqual(
    headerFailures({ "X-Content-Type-Options": "nosniff" }, [
      { name: "x-content-type-options", equals: "nosniff" },
    ]),
    [],
  );
});

test("session cookie: a good login answer", () => {
  const cookie = sessionCookie(
    [
      "labapp_session=abc123; HttpOnly; Path=/; SameSite=Lax; Secure",
    ],
    { secure: true },
  );
  assert.equal(cookie.value, "abc123");
  assert.deepEqual(cookie.failures, []);
});

test("session cookie: on plain http it must not be Secure", () => {
  const cookie = sessionCookie(
    ["labapp_session=abc123; HttpOnly; SameSite=Lax"],
    { secure: false },
  );
  assert.deepEqual(cookie.failures, []);
});

test("session cookie: a missing cookie is a failure with its name", () => {
  const cookie = sessionCookie(["other=1; HttpOnly"], { secure: false });
  assert.equal(cookie.value, null);
  assert.deepEqual(cookie.failures, [
    "the answer sets no labapp_session cookie",
  ]);
});

test("session cookie: each required attribute is checked", () => {
  const noAttributes = sessionCookie(["labapp_session=abc"], {
    secure: false,
  });
  assert.deepEqual(noAttributes.failures, [
    "the labapp_session cookie is not HttpOnly",
    "the labapp_session cookie has no SameSite attribute",
  ]);

  const noSecure = sessionCookie(
    ["labapp_session=abc; HttpOnly; SameSite=Lax"],
    { secure: true },
  );
  assert.deepEqual(noSecure.failures, [
    "the labapp_session cookie is not Secure on an https deployment",
  ]);

  const secureOnHttp = sessionCookie(
    ["labapp_session=abc; HttpOnly; SameSite=Lax; Secure"],
    { secure: false },
  );
  assert.deepEqual(secureOnHttp.failures, [
    "the labapp_session cookie is Secure on a plain http base",
  ]);

  const wrongSameSite = sessionCookie(
    ["labapp_session=abc; HttpOnly; SameSite=Strict"],
    { secure: false },
  );
  assert.deepEqual(wrongSameSite.failures, [
    "the labapp_session cookie has SameSite=Strict, expected SameSite=Lax",
  ]);
});

test("problem body: a good answer has no failure", () => {
  const failures = problemFailures(
    JSON.stringify({
      type: "about:blank",
      title: "Unauthorized",
      status: 401,
      code: "UNAUTHENTICATED",
      detail: "Inicia sesión para continuar.",
    }),
    { contentType: "application/problem+json", status: 401, code: "UNAUTHENTICATED" },
  );
  assert.deepEqual(failures, []);
});

test("problem body: the type, the status and the code are checked", () => {
  const failures = problemFailures(
    JSON.stringify({
      type: "about:blank",
      title: "Unauthorized",
      status: 403,
      code: "FORBIDDEN",
      detail: "No.",
    }),
    { contentType: "application/problem+json", status: 401, code: "UNAUTHENTICATED" },
  );
  assert.deepEqual(failures, [
    "the problem document says status 403, expected 401",
    'the problem document says code "FORBIDDEN", expected "UNAUTHENTICATED"',
  ]);
});

test("problem body: a wrong content type and a body that is not JSON", () => {
  const failures = problemFailures("not json", {
    contentType: "text/html",
    status: 404,
    code: "NOT_FOUND",
  });
  assert.deepEqual(failures, [
    'the answer is "text/html", expected application/problem+json',
    "the body is not JSON",
  ]);
});

test("problem body: a missing detail", () => {
  const failures = problemFailures(
    JSON.stringify({ type: "about:blank", title: "Not Found", status: 404, code: "NOT_FOUND" }),
    { contentType: "application/problem+json", status: 404, code: "NOT_FOUND" },
  );
  assert.deepEqual(failures, ["the problem document has no detail"]);
});

test("retry policy: it stops at the first accepted answer and waits between attempts", async () => {
  const answers = [503, 502, 200].map((status) => ({ status }));
  const calls = [];
  const sleeps = [];
  let now = 1000;
  const result = await retryingFetch(
    "http://example.test/api/health",
    {},
    {
      attempts: 5,
      delayMs: 5000,
      fetchImpl: async (url, init) => {
        calls.push({ url, init });
        return answers.shift();
      },
      sleep: async (milliseconds) => {
        sleeps.push(milliseconds);
        now += milliseconds;
      },
      clock: () => now,
    },
  );
  assert.equal(result.response.status, 200);
  assert.equal(result.attempts, 3);
  assert.deepEqual(sleeps, [5000, 5000]);
  assert.equal(result.waitedMs, 10000);
  assert.equal(calls.length, 3);
  assert.equal(calls[0].url, "http://example.test/api/health");
});

test("retry policy: an answer that never holds is returned after the last attempt", async () => {
  const sleeps = [];
  let now = 0;
  const result = await retryingFetch(
    "http://example.test/api/health",
    {},
    {
      attempts: 5,
      delayMs: 5000,
      fetchImpl: async () => ({ status: 500 }),
      sleep: async (milliseconds) => {
        sleeps.push(milliseconds);
        now += milliseconds;
      },
      clock: () => now,
    },
  );
  assert.equal(result.response.status, 500);
  assert.equal(result.attempts, 5);
  assert.deepEqual(sleeps, [5000, 5000, 5000, 5000]);
  assert.equal(result.waitedMs, 20000);
});

test("retry policy: a failed fetch is retried and the last error is rethrown", async () => {
  let calls = 0;
  const recovered = await retryingFetch(
    "http://example.test/api/health",
    {},
    {
      attempts: 5,
      delayMs: 0,
      fetchImpl: async () => {
        calls += 1;
        if (calls === 1) {
          throw new Error("network down");
        }
        return { status: 200 };
      },
      sleep: async () => {},
    },
  );
  assert.equal(recovered.response.status, 200);
  assert.equal(recovered.attempts, 2);

  calls = 0;
  await assert.rejects(
    retryingFetch(
      "http://example.test/api/health",
      {},
      {
        attempts: 3,
        delayMs: 0,
        fetchImpl: async () => {
          calls += 1;
          throw new Error("network down");
        },
        sleep: async () => {},
      },
    ),
    /network down/,
  );
  assert.equal(calls, 3);
});

test("the demo password comes from the sentence of docs/SEED.md", () => {
  assert.equal(
    demoPassword(
      "All four users share the demo password `Demo-LabApp-2026!`, which the login screen of the demo displays.",
    ),
    "Demo-LabApp-2026!",
  );
  assert.equal(demoPassword("there is no sentence here"), null);
});

test("the first line of a CSV document drops only its line end", () => {
  assert.equal(firstCsvLine("a,b,c\r\n1,2,3\r\n"), "a,b,c");
  assert.equal(firstCsvLine("a,b,c\n1,2,3\n"), "a,b,c");
  assert.equal(firstCsvLine("a,b,c"), "a,b,c");
});
