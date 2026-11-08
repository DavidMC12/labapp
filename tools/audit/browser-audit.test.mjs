// Tests of the argument handling of the browser audit. They never start a browser: a bad --theme stops the
// script before it reads anything else, with exit code 2.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { resourceFailures } from "./resources.mjs";

const script = join(dirname(fileURLToPath(import.meta.url)), "browser-audit.mjs");
const run = (...args) => spawnSync(process.execPath, [script, ...args], { encoding: "utf8", timeout: 20000 });

// The failing-resource check (task 047), on its pure part, without a browser.
const response = (type, status, url = "https://labapp.test/x") => ({ type, status, url });
const state = (expectStatus) => (expectStatus === undefined ? {} : { expectStatus });

test("fails once per document, stylesheet, script, image or font that answers 4xx or 5xx", () => {
  assert.deepEqual(
    resourceFailures(state(), [
      response("Document", 404, "https://labapp.test/no-such-page"),
      response("Stylesheet", 404, "https://labapp.test/missing.css"),
      response("Script", 500, "https://labapp.test/broken.js"),
      response("Image", 404, "https://labapp.test/missing.png"),
      response("Font", 400, "https://labapp.test/missing.woff2"),
    ]),
    [
      "the document https://labapp.test/no-such-page answered 404",
      "the stylesheet https://labapp.test/missing.css answered 404",
      "the script https://labapp.test/broken.js answered 500",
      "the image https://labapp.test/missing.png answered 404",
      "the font https://labapp.test/missing.woff2 answered 400",
    ],
  );
});

test("ignores Fetch and XHR responses and every status under 400", () => {
  assert.equal(
    resourceFailures(state(), [
      response("Fetch", 422, "https://labapp.test/api/orders"),
      response("XHR", 409, "https://labapp.test/api/invoices"),
      response("Document", 200, "https://labapp.test/"),
      response("Stylesheet", 304, "https://labapp.test/globals.css"),
    ]).length,
    0,
  );
});

test("allows the main document to answer expectStatus once, 200 by default", () => {
  const document404 = () => [
    response("Document", 404, "https://labapp.test/no-such-page"),
    response("Stylesheet", 200, "https://labapp.test/globals.css"),
  ];
  // The not-found state answers 404 on purpose.
  assert.deepEqual(resourceFailures({ expectStatus: 404 }, document404()), []);
  // Every other status of the same page fails, and so does 404 on a state that expects 200.
  assert.deepEqual(
    resourceFailures(state(404), [response("Document", 500, "https://labapp.test/no-such-page")]).length,
    1,
  );
  assert.deepEqual(resourceFailures(state(), document404()).length, 1);
});

test("does not let a second document through the expectStatus allowance", () => {
  assert.deepEqual(
    resourceFailures({ expectStatus: 404 }, [
      response("Document", 404, "https://labapp.test/no-such-page"),
      response("Document", 500, "https://labapp.test/another"),
    ]).length,
    1,
  );
});


for (const args of [
  ["--theme", "blue"],
  ["--theme"],
  ["--theme="],
  ["--theme=blue"],
  ["--themes", "dark"],
  ["--theme", "dark", "--theme", "light"],
  ["--theme", "dark", "--theme=light"],
]) {
  test(`rejects ${args.join(" ")}`, () => {
    const result = run(...args);
    assert.equal(result.status, 2, result.stdout + result.stderr);
    assert.match(result.stderr, /--theme must be given once/);
  });
}

for (const args of [
  ["--catalog"],
  ["--catalog", "--json"],
  ["--catalog", "docs/TESTIDS.md", "--only", "login"],
]) {
  test(`rejects ${args.join(" ")}`, () => {
    const result = run(...args);
    assert.equal(result.status, 2, result.stdout + result.stderr);
    assert.match(result.stderr, /--catalog/);
  });
}
