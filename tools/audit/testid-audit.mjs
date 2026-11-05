#!/usr/bin/env node
// Static audit of the test id contract (docs/TESTABILITY.md).
//
// It parses every .tsx file under frontend/src (tests excluded) and reports:
//   - an interactive or semantic element without a test id;
//   - a literal test id that does not match the grammar in src/lib/testid.ts;
//   - a test id expression it cannot check, outside the UI primitives.
// A JSX attribute whose value is a constant or a property ending in "testId" is accepted
// without being followed, because the literal it holds is checked where it is written: every
// `const xTestId = "..."` and every `testId: "..."` in a .ts or .tsx file must match the grammar
// (the TypeScript type `TestId` does not check casing or word structure). Uniqueness inside one
// rendered page is a property of the DOM, not of the source, so it is left to the browser audit.
// Exit code 1 when anything is reported.
import { createRequire } from "node:module";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "..", "..");
const frontendRoot = resolve(process.env.AUDIT_FRONTEND ?? join(repoRoot, "frontend"));
const require = createRequire(join(frontendRoot, "package.json"));
const ts = require("typescript");

// Plain elements that must carry a test id, and the components that take a `testId` prop.
export const REQUIRED_ELEMENTS = new Set([
  "button", "a", "input", "select", "textarea", "form", "table", "h1", "h2", "h3", "dialog",
]);
export const ID_COMPONENTS = new Set(["Button", "Input", "Select", "Textarea", "Link"]);
const REQUIRED_ROLES = new Set(["alert", "status"]);
const ID_ATTRIBUTES = new Set(["data-testid", "testId"]);

export function loadPattern(root = frontendRoot) {
  const source = readFileSync(join(root, "src", "lib", "testid.ts"), "utf8");
  const match = /export const TEST_ID_PATTERN =\s*\/(.+)\/;/.exec(source);
  if (!match) throw new Error("TEST_ID_PATTERN not found in src/lib/testid.ts");
  return new RegExp(match[1]);
}

function* sourceFiles(directory) {
  for (const name of readdirSync(directory)) {
    const path = join(directory, name);
    if (statSync(path).isDirectory()) {
      yield* sourceFiles(path);
    } else if (/\.tsx?$/.test(name) && !/\.(test|d)\.tsx?$/.test(name)) {
      yield path;
    }
  }
}

/** The possible literal values of an id expression, or null when it cannot be checked. */
function literalValues(expression) {
  if (ts.isStringLiteral(expression) || ts.isNoSubstitutionTemplateLiteral(expression)) {
    return [expression.text];
  }
  if (ts.isTemplateExpression(expression)) {
    // `customers-list-row-${customer.id}` is checked with a sample number in place of the hole.
    return [expression.head.text + expression.templateSpans.map((s) => "7" + s.literal.text).join("")];
  }
  if (ts.isConditionalExpression(expression)) {
    const whenTrue = literalValues(expression.whenTrue);
    const whenFalse = literalValues(expression.whenFalse);
    return whenTrue && whenFalse ? [...whenTrue, ...whenFalse] : null;
  }
  if (ts.isParenthesizedExpression(expression)) return literalValues(expression.expression);
  return null;
}

function unwrap(expression) {
  let current = expression;
  while (ts.isAsExpression(current) || ts.isSatisfiesExpression(current) || ts.isParenthesizedExpression(current)) {
    current = current.expression;
  }
  return current;
}

function isTypedIdReference(expression) {
  if (ts.isIdentifier(expression)) return /testid$/i.test(expression.text);
  if (ts.isPropertyAccessExpression(expression)) return /testid$/i.test(expression.name.text);
  return false;
}

function attributeMap(attributes) {
  const map = new Map();
  for (const attribute of attributes.properties) {
    if (ts.isJsxAttribute(attribute)) map.set(attribute.name.getText(), attribute);
  }
  return map;
}

function attributeExpression(attribute) {
  const value = attribute.initializer;
  if (!value) return null;
  if (ts.isStringLiteral(value)) return value;
  if (ts.isJsxExpression(value) && value.expression) return value.expression;
  return null;
}

export function auditSource(fileName, text, pattern, inPrimitives = false) {
  const problems = [];
  const literals = [];
  const kind = fileName.endsWith(".ts") ? ts.ScriptKind.TS : ts.ScriptKind.TSX;
  const sourceFile = ts.createSourceFile(fileName, text, ts.ScriptTarget.Latest, true, kind);

  const report = (node, message) => {
    const { line } = sourceFile.getLineAndCharacterOfPosition(node.getStart());
    problems.push({ file: fileName, line: line + 1, message });
  };

  const checkLiteral = (node, expression) => {
    for (const value of literalValues(expression) ?? []) {
      if (!pattern.test(value)) report(node, `test id "${value}" does not match the grammar`);
    }
  };

  const visit = (node) => {
    // `const loginHeadingTestId: TestId = "..."` and `{ testId: "..." }`: the literal is checked here.
    if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) && /testid$/i.test(node.name.text) && node.initializer) {
      checkLiteral(node, unwrap(node.initializer));
    }
    if (ts.isPropertyAssignment(node) && /^testid$/i.test(node.name.getText().replace(/["']/g, ""))) {
      checkLiteral(node, unwrap(node.initializer));
    }
    if (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) {
      const name = node.tagName.getText();
      const attributes = attributeMap(node.attributes);
      const hasSpread = node.attributes.properties.some((p) => ts.isJsxSpreadAttribute(p));
      const idAttribute = [...ID_ATTRIBUTES].map((a) => attributes.get(a)).find(Boolean);
      const role = attributes.get("role") ? attributeExpression(attributes.get("role"))?.text : undefined;

      const typeAttribute = attributes.get("type") ? attributeExpression(attributes.get("type"))?.text : undefined;
      const hiddenInput = name === "input" && typeAttribute === "hidden";
      const needsId =
        !hiddenInput &&
        (REQUIRED_ELEMENTS.has(name) || ID_COMPONENTS.has(name) || (role !== undefined && REQUIRED_ROLES.has(role)));

      if (idAttribute) {
        const expression = attributeExpression(idAttribute);
        const values = expression ? literalValues(expression) : null;
        if (values) {
          for (const value of values) {
            if (!pattern.test(value)) report(node, `test id "${value}" does not match the grammar`);
            else literals.push({ value, line: sourceFile.getLineAndCharacterOfPosition(node.getStart()).line + 1 });
          }
        } else if (!inPrimitives && !(expression && isTypedIdReference(expression))) {
          report(node, `<${name}> has a test id that cannot be checked statically (${expression?.getText() ?? "no value"})`);
        }
      } else if (needsId && !(inPrimitives && hasSpread)) {
        report(node, `<${name}${role ? ` role="${role}"` : ""}> has no test id`);
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sourceFile);
  return { problems, literals };
}

export function audit(root = frontendRoot) {
  const pattern = loadPattern(root);
  const src = join(root, "src");
  const primitives = join(src, "components", "ui") + sep;
  const problems = [];
  let ids = 0;
  let files = 0;
  for (const file of sourceFiles(src)) {
    files += 1;
    const display = relative(dirname(root), file);
    const result = auditSource(display, readFileSync(file, "utf8"), pattern, file.startsWith(primitives));
    problems.push(...result.problems);
    ids += result.literals.length;
  }
  return { files, ids, problems };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const { files, ids, problems } = audit();
  for (const problem of problems) console.error(`${problem.file}:${problem.line}: ${problem.message}`);
  console.log(`Test id audit: ${files} files, ${ids} literal ids, ${problems.length} problem(s).`);
  process.exit(problems.length === 0 ? 0 : 1);
}
