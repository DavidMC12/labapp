import assert from "node:assert/strict";
import { cpSync, mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { audit, auditSource, loadPattern } from "./testid-audit.mjs";

const pattern = loadPattern();
const check = (code, inPrimitives = false) => auditSource("fixture.tsx", code, pattern, inPrimitives).problems;
const messages = (code, inPrimitives = false) => check(code, inPrimitives).map((p) => p.message);

test("accepts elements that carry a valid test id", () => {
  assert.deepEqual(
    check(`export const A = () => <div><button data-testid="customers-list-new-button">x</button><Input testId="customers-form-name-input" label="x" /></div>;`),
    [],
  );
});

test("reports an interactive element without a test id", () => {
  assert.deepEqual(messages(`export const A = () => <button onClick={f}>x</button>;`), ["<button> has no test id"]);
  assert.deepEqual(messages(`export const A = () => <a href="/x">x</a>;`), ["<a> has no test id"]);
  assert.deepEqual(messages(`export const A = () => <form onSubmit={f} />;`), ["<form> has no test id"]);
});

test("reports a UI component without testId", () => {
  assert.deepEqual(messages(`export const A = () => <Button onClick={f}>x</Button>;`), ["<Button> has no test id"]);
  assert.deepEqual(messages(`export const A = () => <Link href="/x">x</Link>;`), ["<Link> has no test id"]);
});

test("reports alert and status elements without a test id", () => {
  assert.deepEqual(messages(`export const A = () => <p role="alert">x</p>;`), [`<p role="alert"> has no test id`]);
  assert.deepEqual(messages(`export const A = () => <div role="status">x</div>;`), [`<div role="status"> has no test id`]);
  assert.deepEqual(check(`export const A = () => <p role="alert" data-testid="app-shell-error-alert">x</p>;`), []);
});

test("reports an id that breaks the grammar", () => {
  assert.deepEqual(messages(`export const A = () => <button data-testid="submit">x</button>;`), [
    `test id "submit" does not match the grammar`,
  ]);
  assert.deepEqual(messages(`export const A = () => <button data-testid="Customers-List-New-Button">x</button>;`).length, 1);
  assert.deepEqual(messages(`export const A = () => <button data-testid="customers-list-new">x</button>;`).length, 1);
});

test("checks template literals with a sample number and both branches of a conditional", () => {
  assert.deepEqual(check("export const A = ({ c }) => <tr data-testid={`customers-list-row-${c.id}`} />;"), []);
  assert.deepEqual(messages("export const A = ({ c }) => <tr data-testid={`customers-list-row${c.id}`} />;").length, 1);
  assert.deepEqual(
    check(`export const A = ({ a }) => <Button testId={a ? "customers-detail-deactivate-button" : "customers-detail-reactivate-button"} />;`),
    [],
  );
  assert.equal(
    messages(`export const A = ({ a }) => <Button testId={a ? "customers-detail-deactivate-button" : "oops"} />;`).length,
    1,
  );
});

test("accepts a typed id reference but not an arbitrary expression", () => {
  assert.deepEqual(check(`export const A = () => <h1 data-testid={headingTestId}>x</h1>;`), []);
  assert.deepEqual(check(`export const A = ({ u }) => <li data-testid={u.testId} />;`), []);
  assert.equal(messages(`export const A = ({ id }) => <h1 data-testid={build(id)}>x</h1>;`).length, 1);
});

test("allows spread props only inside the UI primitives", () => {
  const code = `export const A = (props) => <button {...props} />;`;
  assert.deepEqual(messages(code), ["<button> has no test id"]);
  assert.deepEqual(check(code, true), []);
});

test("elements outside the required set need no id", () => {
  assert.deepEqual(check(`export const A = () => <div><p>x</p><span>y</span><ul><li>z</li></ul></div>;`), []);
});

test("checks the literal of a typed id constant and of a testId property", () => {
  assert.deepEqual(check(`const headingTestId: TestId = "orders-list-heading";`), []);
  assert.equal(messages(`const badTestId: TestId = "customers-Bad_Name-button";`).length, 1);
  assert.equal(messages(`const x = { email: "a", testId: "bad" };`).length, 1);
  assert.equal(messages(`const x = { "testId": "auth-login-demo-item-1" as const };`).length, 0);
  assert.equal(messages(`export const ITEMS = [{ testId: "nope" }];`).length, 1);
});

test("a hidden input needs no id", () => {
  assert.deepEqual(check(`export const A = () => <input type="hidden" name="x" />;`), []);
  assert.equal(messages(`export const A = () => <input type="text" name="x" />;`).length, 1);
});

test("a tree with a violation fails the audit", () => {
  const root = mkdtempSync(join(tmpdir(), "audit-"));
  mkdirSync(join(root, "src", "lib"), { recursive: true });
  cpSync(join(import.meta.dirname, "..", "..", "frontend", "src", "lib", "testid.ts"), join(root, "src", "lib", "testid.ts"));
  writeFileSync(join(root, "src", "page.tsx"), `export const P = () => <button onClick={f}>x</button>;`);
  writeFileSync(join(root, "src", "data.ts"), `export const D = { testId: "wrong" };`);
  const result = audit(root);
  assert.equal(result.problems.length, 2);
});

test("the real frontend passes", () => {
  const result = audit();
  assert.deepEqual(result.problems, []);
  assert.ok(result.files > 10);
});
