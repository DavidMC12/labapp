import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * The tokens of the "Libro mayor" theme are read back from globals.css, so
 * the test verifies the file the app really ships and fails if a value is
 * edited without checking its contrast again.
 */

type ColorName = string;

function readTokens(): Map<ColorName, string> {
  // `import.meta.url` is not `file:` inside the jsdom environment; the
  // test always runs from `frontend/` (`pnpm test`), so cwd is the anchor.
  const css = readFileSync(join(process.cwd(), "src/app/globals.css"), "utf8");
  const tokens = new Map<ColorName, string>();
  const declaration = /--([a-z-]+):\s*(#[0-9a-fA-F]{6})\s*;/g;
  for (const match of css.matchAll(declaration)) {
    tokens.set(match[1], match[2]);
  }
  return tokens;
}

/** WCAG relative luminance of a hex color. */
function relativeLuminance(hex: string): number {
  const channels = [1, 3, 5].map((start) =>
    parseInt(hex.slice(start, start + 2), 16) / 255,
  );
  const [r, g, b] = channels.map((value) =>
    value <= 0.03928 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4),
  );
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** WCAG contrast ratio of two hex colors. */
function contrastRatio(foregroundHex: string, backgroundHex: string): number {
  const [first, second] = [
    relativeLuminance(foregroundHex),
    relativeLuminance(backgroundHex),
  ].sort((a, b) => b - a);
  return (first + 0.05) / (second + 0.05);
}

const REQUIRED_CONTRAST: [foreground: string, background: string, minimum: number][] = [
  ["ink", "paper", 4.5],
  ["muted", "paper", 4.5],
  ["muted", "surface", 4.5],
  ["rail-ink", "rail", 4.5],
  ["rail-muted", "rail", 4.5],
  ["rail-muted", "rail-hover", 4.5],
  ["accent-ink", "accent", 4.5],
  ["accent-ink", "accent-hover", 4.5],
  ["accent", "ok-bg", 4.5],
  ["muted", "off-bg", 4.5],
  ["danger", "danger-bg", 4.5],
  ["danger", "paper", 4.5],
  ["danger", "surface", 4.5],
  ["accent", "paper", 4.5],
  ["control-border", "surface", 3],
  ["focus", "paper", 3],
  ["focus", "rail", 3],
];

const REQUIRED_TOKENS = [
  "paper",
  "surface",
  "ink",
  "muted",
  "line",
  "control-border",
  "rail",
  "rail-ink",
  "rail-muted",
  "rail-hover",
  "accent",
  "accent-hover",
  "accent-ink",
  "ok-bg",
  "off-bg",
  "danger",
  "danger-bg",
  "focus",
];

describe("the Libro mayor design tokens", () => {
  it("defines every token of the theme in globals.css", () => {
    const tokens = readTokens();

    for (const name of REQUIRED_TOKENS) {
      expect(tokens.get(name), name).toMatch(/^#[0-9a-fA-F]{6}$/);
    }
  });

  it("keeps the WCAG contrast of every checked pair", () => {
    const tokens = readTokens();

    for (const [foreground, background, minimum] of REQUIRED_CONTRAST) {
      const fg = tokens.get(foreground);
      const bg = tokens.get(background);
      expect(fg, `token ${foreground}`).toBeDefined();
      expect(bg, `token ${background}`).toBeDefined();
      const ratio = contrastRatio(fg as string, bg as string);
      expect(ratio, `${foreground}/${background}: ${ratio.toFixed(2)}`)
        .toBeGreaterThanOrEqual(minimum);
    }
  });
});
