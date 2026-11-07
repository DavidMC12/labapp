// Tests of the argument handling of the browser audit. They never start a browser: a bad --theme stops the
// script before it reads anything else, with exit code 2.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const script = join(dirname(fileURLToPath(import.meta.url)), "browser-audit.mjs");
const run = (...args) => spawnSync(process.execPath, [script, ...args], { encoding: "utf8", timeout: 20000 });

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
