#!/usr/bin/env node
// Documentation linter: the documents are part of the product (the owner's tests
// rely on them), so their mechanical mistakes are checked like code. It reads
// every *.md under the repository root except the historical records
// (docs/reviews, docs/tasks) and the usual ignored trees (hidden directories,
// node_modules), and reports:
//   - a relative Markdown link to a file or directory that does not exist, or
//     to a path outside the repository, or to an anchor no heading provides;
//   - an inline code span that matches the test id grammar (read from
//     frontend/src/lib/testid.ts, one definition) yet is neither in
//     docs/TESTIDS.md, nor a literal id of the frontend source, nor a
//     documented template (it contains { } or ends with -N);
//   - a code fence that is never closed;
//   - a table row with more or fewer cells than its header.
// Absolute URLs and mailto: are not fetched. Options: --root <dir> to lint a
// different tree (the tests use it), --json to print the list of problems as
// JSON instead of one line per problem. Exit code 1 when there is any problem.
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const defaultRoot = resolve(here, "..", "..");

export function loadPattern(root = defaultRoot) {
  const source = readFileSync(join(root, "frontend", "src", "lib", "testid.ts"), "utf8");
  const match = /export const TEST_ID_PATTERN =\s*\/(.+)\/;/.exec(source);
  if (!match) throw new Error("TEST_ID_PATTERN not found in frontend/src/lib/testid.ts");
  return new RegExp(match[1]);
}

/** The Markdown files to lint, in a deterministic order. */
export function collectMarkdownFiles(root) {
  const files = [];
  const walk = (dir) => {
    for (const name of readdirSync(dir).sort()) {
      const path = join(dir, name);
      let stats;
      try {
        stats = statSync(path);
      } catch {
        continue;
      }
      if (stats.isDirectory()) {
        if (name.startsWith(".") || name === "node_modules") continue;
        const rel = relative(root, path);
        if (rel === join("docs", "reviews") || rel === join("docs", "tasks")) continue;
        walk(path);
      } else if (name.endsWith(".md")) {
        files.push(path);
      }
    }
  };
  walk(root);
  return files;
}

/** The contents of the inline code spans of a block of Markdown, in reading order. */
export function codeSpans(text) {
  const spans = [];
  for (const line of text.split("\n")) {
    if (/^\s*(```|~~~)/.test(line)) continue;
    const runs = [];
    for (const match of line.matchAll(/`+/g)) runs.push({ start: match.index, end: match.index + match[0].length });
    for (let index = 0; index + 1 < runs.length; index += 2) {
      const span = line.slice(runs[index].end, runs[index + 1].start);
      if (span) spans.push(span);
    }
  }
  return spans;
}

/** GitHub's heading anchor rule: lower case, punctuation removed, spaces to hyphens. */
export function githubSlug(text) {
  return text
    .replace(/`+/g, "")
    .trim()
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s_-]/gu, "")
    .replace(/\s/g, "-");
}

const headingCache = new Map();

/** The anchors of a Markdown file (a repeated heading gets the GitHub -1, -2 suffix). */
function headingsOf(path) {
  if (!headingCache.has(path)) {
    const slugs = [];
    const seen = new Map();
    for (const line of readFileSync(path, "utf8").split("\n")) {
      if (/^\s*(```|~~~)/.test(line)) continue;
      const heading = /^#{1,6}\s+(.+)$/.exec(line);
      if (!heading) continue;
      const base = githubSlug(heading[1].replace(/[#\s]+$/, ""));
      const count = seen.get(base) ?? 0;
      seen.set(base, count + 1);
      slugs.push(count === 0 ? base : `${base}-${count}`);
    }
    headingCache.set(path, slugs);
  }
  return headingCache.get(path);
}

/** Splits a table line into its cells; an escaped pipe (\|) stays inside a cell. */
function cellsOf(line) {
  let text = line.trim();
  if (text.startsWith("|")) text = text.slice(1);
  if (text.endsWith("|")) text = text.slice(0, -1);
  return text.split(/(?<!\\)\|/);
}

const isDelimiterRow = (line) =>
  line.trim().startsWith("|") && cellsOf(line).every((cell) => /^:?-{1,}:?$/.test(cell.trim()));

/** One file's problems, in reading order. */
export function checkFile(root, path, pattern, knownIds) {
  const problems = [];
  const file = relative(root, path);
  const lines = readFileSync(path, "utf8").split("\n");

  const checkLinkTarget = (lineNumber, target) => {
    // A URL scheme (http:, mailto:, ...) means the link is not fetched.
    if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(target)) return;
    const hash = target.indexOf("#");
    const destination = hash === -1 ? target : target.slice(0, hash);
    const anchor = hash === -1 ? "" : target.slice(hash + 1);
    let decodedAnchor = anchor;
    let decoded;
    try {
      decoded = decodeURIComponent(destination || "");
      decodedAnchor = decodeURIComponent(anchor).toLowerCase();
    } catch {
      // An encoding the browser could not resolve either: the raw path never exists.
    }
    const base =
      destination === ""
        ? path
        : destination.startsWith("/")
          ? resolve(root, "." + decoded)
          : resolve(dirname(path), decoded);
    if (base !== root && !base.startsWith(root + sep)) {
      problems.push({ file, line: lineNumber, message: `link "${target}" escapes the repository` });
      return;
    }
    if (!existsSync(base)) {
      problems.push({ file, line: lineNumber, message: `link "${target}" points to a path that does not exist` });
      return;
    }
    if (anchor !== "" && statSync(base).isFile() && base.endsWith(".md") && !headingsOf(base).includes(decodedAnchor)) {
      problems.push({ file, line: lineNumber, message: `anchor "#${anchor}" does not match any heading of "${destination}"` });
    }
  };

  let fence = null; // the character (` or ~) and the length of the open fence
  for (let index = 0; index < lines.length; index++) {
    const lineNumber = index + 1;
    const line = lines[index];
    const marker = /^\s{0,3}(`{3,}|~{3,})/.exec(line);
    if (marker) {
      if (!fence) fence = { char: marker[1][0], length: marker[1].length };
      else if (marker[1][0] === fence.char && marker[1].length >= fence.length) fence = null;
      continue;
    }
    if (fence) continue;

    if (line.trim().startsWith("|")) {
      // A table: the header line is followed by a delimiter line, and every
      // row after the delimiter must have as many cells as the header.
      if (index + 1 < lines.length && isDelimiterRow(lines[index + 1])) {
        const headerCells = cellsOf(line).filter((cell) => cell.trim() !== "").length;
        let cursor = index + 2;
        while (cursor < lines.length && lines[cursor].trim().startsWith("|") && !/^\s*(`{3,}|~{3,})/.test(lines[cursor])) {
          const cells = cellsOf(lines[cursor]).length;
          if (cells > 0 && cells !== headerCells) {
            problems.push({ file, line: cursor + 1, message: `table row has ${cells} cell(s), the header has ${headerCells}` });
          }
          cursor++;
        }
        index = cursor - 1;
        continue;
      }
    }

    for (const match of line.matchAll(/\[([^\]]*)\]\(\s*([^)\s]+)[^)]*\)/g)) {
      checkLinkTarget(lineNumber, match[2]);
    }

    for (const span of codeSpans(line)) {
      const id = span.trim();
      if (!pattern.test(id)) continue;
      if (knownIds.has(id)) continue;
      if (id.includes("{") && id.includes("}")) continue; // a documented template
      if (/-\d+$/.test(id)) continue; // a record id or a list position: also a template
      problems.push({
        file,
        line: lineNumber,
        message: `test id "${id}" is not a documented template and appears neither in docs/TESTIDS.md nor in the frontend source`,
      });
    }
  }

  if (fence) {
    const openLine = lines.findIndex((text) => /^\s{0,3}(`{3,}|~{3,})/.exec(text));
    problems.push({ file, line: openLine + 1, message: "code fence is never closed" });
  }

  return problems;
}

/** The ids the catalog documents: every code span of docs/TESTIDS.md that matches the grammar. */
export function catalogIds(root = defaultRoot, pattern) {
  const ids = new Set();
  const catalog = join(root, "docs", "TESTIDS.md");
  if (!existsSync(catalog)) return ids;
  for (const span of codeSpans(readFileSync(catalog, "utf8"))) {
    if (pattern.test(span.trim())) ids.add(span.trim());
  }
  return ids;
}

/** The ids the frontend source knows: every quoted string (.ts/.tsx, tests excluded) that matches the grammar. */
export function sourceIds(root = defaultRoot, pattern) {
  const ids = new Set();
  const sourceRoot = join(root, "frontend", "src");
  if (!existsSync(sourceRoot)) return ids;
  const walk = (dir) => {
    for (const name of readdirSync(dir).sort()) {
      const path = join(dir, name);
      if (statSync(path).isDirectory()) walk(path);
      else if (/\.tsx?$/.test(name) && !/\.(test|d)\.tsx?$/.test(name)) {
        const source = readFileSync(path, "utf8");
        for (const match of source.matchAll(/"([^"\n]+)"|'([^'\n]+)'|`([^`\n]+)`/g)) {
          const value = match[1] ?? match[2] ?? match[3];
          if (pattern.test(value.trim())) ids.add(value.trim());
        }
      }
    }
  };
  walk(sourceRoot);
  return ids;
}

/** Every check over one tree. */
export function lint(root = defaultRoot) {
  const pattern = loadPattern(root);
  const knownIds = new Set([...catalogIds(root, pattern), ...sourceIds(root, pattern)]);
  const files = collectMarkdownFiles(root);
  const problems = [];
  for (const path of files) problems.push(...checkFile(root, path, pattern, knownIds));
  return { files: files.length, ids: knownIds.size, problems };
}

function usage() {
  console.error("usage: node tools/audit/docs-lint.mjs [--root <dir>] [--json]");
  process.exit(2);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  const rootArg = args.indexOf("--root");
  const json = args.includes("--json");
  let root = defaultRoot;
  if (rootArg !== -1) {
    if (rootArg + 1 >= args.length) usage();
    root = resolve(args[rootArg + 1]);
  }
  const { files, ids, problems } = lint(root);
  if (json) console.log(JSON.stringify(problems, null, 2));
  else {
    for (const problem of problems) console.error(`${problem.file}:${problem.line} ${problem.message}`);
    console.log(`Documentation lint: ${files} file(s), ${ids} known id(s), ${problems.length} problem(s).`);
  }
  process.exit(problems.length === 0 ? 0 : 1);
}
