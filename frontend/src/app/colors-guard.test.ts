import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * The dark theme arrives in a later task and must be buildable by changing
 * globals.css alone. These scans fail for any literal color written
 * outside of it.
 */

const SRC_ROOT = join(process.cwd(), "src");

/** Paths never scanned: the token file and the tests themselves. */
const EXCLUDED = ["app/globals.css"];

/** Every color function format that would bypass the tokens. */
const COLOR_FUNCTIONS = [
  "rgba\\(",
  "rgb\\(",
  "hsla\\(",
  "hsl\\(",
  "oklch\\(",
  "oklab\\(",
  "lab\\(",
  "lch\\(",
  "hwb\\(",
  "color\\(",
  "color-mix\\(",
];

/**
 * Tailwind palette classes. `transparent`, `currentColor` and `inherit`
 * are not palette colors; every named Tailwind color and white/black is.
 */
const PALETTE_CLASS =
  /\b(bg|text|border|ring|outline|fill|stroke|divide|from|via|to|decoration|accent|caret|shadow)-(slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|white|black)\b/g;

function scanFiles(dir: string, files: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) {
      scanFiles(path, files);
    } else if (
      /\.(ts|tsx|css)$/.test(entry)
      && !/\.test\./.test(entry)
      && !EXCLUDED.includes(relative(SRC_ROOT, path).split(sep).join("/"))
    ) {
      files.push(path);
    }
  }
  return files;
}

function findViolations(text: string): string[] {
  const violations: string[] = [];
  const hex = /#[0-9a-fA-F]{3,8}\b/g;
  for (const match of text.matchAll(hex)) {
    violations.push(`hex color ${match[0]}`);
  }
  for (const fn of COLOR_FUNCTIONS) {
    const literal = new RegExp(fn, "g");
    for (const match of text.matchAll(literal)) {
      violations.push(`color function ${match[0]}`);
    }
  }
  for (const match of text.matchAll(PALETTE_CLASS)) {
    violations.push(`palette class ${match[0]}`);
  }
  return [...new Set(violations)];
}

describe("the sources contain no literal colors", () => {
  it("scans every .ts, .tsx and .css under src except globals.css and the tests", () => {
    expect(scanFiles(SRC_ROOT).length).toBeGreaterThan(0);
  });

  for (const file of scanFiles(SRC_ROOT)) {
    it(`keeps ${relative(SRC_ROOT, file).split(sep).join("/")} free of literal colors`, () => {
      const text = readFileSync(file, "utf8");
      expect(findViolations(text)).toEqual([]);
    });
  }
});
