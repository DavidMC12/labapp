import assert from "node:assert/strict";
import { cpSync, mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { collectMarkdownFiles, githubSlug, lint } from "./docs-lint.mjs";

/** A temporary tree with the real test id grammar, ready to hold documents. */
const makeTree = () => {
  const root = mkdtempSync(join(tmpdir(), "docslint-"));
  mkdirSync(join(root, "frontend", "src", "lib"), { recursive: true });
  cpSync(
    join(import.meta.dirname, "..", "..", "frontend", "src", "lib", "testid.ts"),
    join(root, "frontend", "src", "lib", "testid.ts"),
  );
  return root;
};

const write = (root, relativePath, text) => {
  mkdirSync(dirname(join(root, relativePath)), { recursive: true });
  writeFileSync(join(root, relativePath), text);
};

/** A well-formed tree: links resolve, anchors exist, the table is even. */
const goodTree = (root) => {
  write(root, "docs/TESTIDS.md", "# Test id catalog\n\n| Test id | Element |\n|---|---|\n| `app-nav-home-link` | `a` |\n");
  write(root, "README.md", [
    "# Title",
    "",
    "## Setup guide",
    "",
    "See [Tests](#setup-guide), [docs/TESTIDS.md](docs/TESTIDS.md), [audit](docs/).",
    "The catalog id `app-nav-home-link` and the template `orders-detail-line-row-{line_id}` are fine.",
    "Nothing is fetched from [https://example.com](https://example.com) or [mail](mailto:dev@example.test).",
    "",
    "| A | B |",
    "|---|---|",
    "| 1 | 2 |",
    "```ts",
    "const fence = true;",
    "```",
    "",
  ].join("\n"));
};

test("a good tree passes", () => {
  const root = makeTree();
  goodTree(root);
  assert.deepEqual(lint(root).problems, []);
});

test("a link to a missing file fails with the file and line", () => {
  const root = makeTree();
  write(root, "README.md", "First line.\n\n[A](docs/DEVELOPMENT.md)\n");
  assert.deepEqual(lint(root).problems, [
    { file: "README.md", line: 3, message: "link \"docs/DEVELOPMENT.md\" points to a path that does not exist" },
  ]);
});

test("a link to a missing anchor fails, an existing one passes", () => {
  const root = makeTree();
  write(root, "docs/TESTIDS.md", "# Test id catalog\n");
  write(root, "README.md", "[a](docs/TESTIDS.md#test-id-catalog) [b](docs/TESTIDS.md#no-heading)\n");
  assert.deepEqual(lint(root).problems, [
    { file: "README.md", line: 1, message: 'anchor "#no-heading" does not match any heading of "docs/TESTIDS.md"' },
  ]);
});

test("a link that escapes the repository fails", () => {
  const root = makeTree();
  write(root, "README.md", "[x](../outside.md)\n");
  assert.deepEqual(lint(root).problems, [{ file: "README.md", line: 1, message: "link \"../outside.md\" escapes the repository" }]);
});

test("an unknown test id fails with the file and line", () => {
  const root = makeTree();
  write(root, "docs/README.md", "The button is `products-catalog-gadget-button`.\n");
  assert.deepEqual(lint(root).problems, [
    {
      file: "docs/README.md",
      line: 1,
      message:
        'test id "products-catalog-gadget-button" is not a documented template and appears neither in docs/TESTIDS.md nor in the frontend source',
    },
  ]);
});

test("a catalog id and a template id pass", () => {
  const root = makeTree();
  write(root, "docs/TESTIDS.md", "# c\n\n| Test id | Element |\n|---|---|\n| `app-nav-home-link` | `a` |\n");
  write(root, "docs/README.md", "Ids: `app-nav-home-link`, `orders-detail-line-row-{line_id}`, `customers-list-row-7`.\n");
  assert.deepEqual(lint(root).problems, []);
});

test("an id the frontend source contains passes", () => {
  const root = makeTree();
  write(root, "docs/README.md", "See `settings-taxrate-readonly-text`.\n");
  write(root, "frontend/src/app/page.tsx", 'export const x = { data: "settings-taxrate-readonly-text" };\n');
  assert.deepEqual(lint(root).problems, []);
});

test("an unclosed code fence fails at the opening line", () => {
  const root = makeTree();
  write(root, "README.md", "# Title\n\n```ts\nconst open = true;\n");
  assert.deepEqual(lint(root).problems, [{ file: "README.md", line: 3, message: "code fence is never closed" }]);
});

test("a ragged table row fails", () => {
  const root = makeTree();
  write(root, "README.md", "| A | B | C |\n|---|---|---|\n| 1 | 2 |\n| 1 | 2 | 3 |\n");
  assert.deepEqual(lint(root).problems, [{ file: "README.md", line: 3, message: "table row has 2 cell(s), the header has 3" }]);
});

test("excluded trees are skipped", () => {
  const root = makeTree();
  const bad = "----\n| A |\n|---|\n| 1 | 2 |\n[x](nowhere.md)\n`products-catalog-gadget-button`\n```ts";
  write(root, "docs/reviews/2026-01-01-a.md", bad);
  write(root, "docs/tasks/001-a.md", bad);
  write(root, "node_modules/pkg/README.md", bad);
  write(root, ".venv/lib/README.md", bad);
  assert.deepEqual(lint(root).problems, []);
  assert.deepEqual(collectMarkdownFiles(root).map((p) => p.slice(root.length + 1)), []);
});

test("the anchor rule follows GitHub's slug rule", () => {
  assert.equal(githubSlug("App Shell"), "app-shell");
  assert.equal(githubSlug("What is next?"), "what-is-next");
  assert.equal(githubSlug("Fees, tax (USD)"), "fees-tax-usd");
  assert.equal(githubSlug("`tax_rate` field"), "tax_rate-field");
});

test("the real repository passes", () => {
  const result = lint();
  assert.deepEqual(result.problems, [], JSON.stringify(result.problems));
  assert.ok(result.files > 10);
});

