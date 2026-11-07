import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * The tokens of the "Libro mayor" theme are read back from globals.css,
 * so the test verifies the file the app really ships and fails if a value
 * is edited without checking its contrast again.
 *
 * The light values live on bare `:root`; the dark theme redefines every
 * token in exactly two places, the system default inside the
 * `prefers-color-scheme` media query (pinned back to light only by
 * `data-theme="light"` on `<html>`) and the explicit `data-theme="dark"`
 * choice. Nothing may be defined only inside a media query or an
 * attribute selector, so the tests parse the three places separately.
 */

type ColorName = string;
type TokenBlock = Map<ColorName, string>;

/** The body of the first rule matching the selector, or null. */
function ruleBody(css: string, selector: RegExp): string | null {
  const match = selector.exec(css);
  if (!match) {
    return null;
  }
  const open = css.indexOf("{", match.index);
  const close = css.indexOf("}", open);
  if (open === -1 || close === -1) {
    return null;
  }
  return css.slice(open + 1, close);
}

/** The hex color declarations of a rule body, keyed by token name. */
function parseTokens(body: string): TokenBlock {
  const tokens = new Map<ColorName, string>();
  const declaration = /--([a-z-]+):\s*(#[0-9a-fA-F]{6})\s*;/g;
  for (const match of body.matchAll(declaration)) {
    tokens.set(match[1], match[2]);
  }
  return tokens;
}

/**
 * `import.meta.url` is not `file:` inside the jsdom environment; the test
 * always runs from `frontend/` (`pnpm test`), so cwd is the anchor.
 */
function readPlaces(): {
  light: TokenBlock;
  systemDark: TokenBlock;
  explicitDark: TokenBlock;
} {
  const css = readFileSync(join(process.cwd(), "src/app/globals.css"), "utf8");
  const light = ruleBody(css, /^:root \{/m);
  const systemDark = ruleBody(
    css,
    /:root:not\(\[data-theme="light"\]\) \{/,
  );
  const explicitDark = ruleBody(css, /^:root\[data-theme="dark"\] \{/m);

  expect(light, "the bare :root block").not.toBeNull();
  expect(systemDark, "the dark media query block").not.toBeNull();
  expect(explicitDark, "the data-theme dark block").not.toBeNull();

  return {
    light: parseTokens(light as string),
    systemDark: parseTokens(systemDark as string),
    explicitDark: parseTokens(explicitDark as string),
  };
}

/** Whether the rule body declares the given `color-scheme` value. */
function matchingScheme(body: string, scheme: string): boolean {
  const declaration = new RegExp(
    `color-scheme:\\s*${scheme}\\s*;`,
  );
  return declaration.test(body);
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

/** The contrast pairs of the dark theme, with the same minimums. */
const REQUIRED_DARK_CONTRAST: [foreground: string, background: string, minimum: number][] = [
  ["ink", "paper", 4.5],
  ["ink", "surface", 4.5],
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
  ["accent", "paper", 4.5],
  ["accent", "surface", 4.5],
  ["danger", "paper", 4.5],
  ["danger", "surface", 4.5],
  ["control-border", "surface", 3],
  ["control-border", "paper", 3],
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

/** The dark values of the theme, exactly as the brief fixes them. */
const DARK_TOKENS: Record<ColorName, string> = {
  paper: "#111513",
  surface: "#1A1F1C",
  ink: "#E8EEEA",
  muted: "#9FB0A7",
  line: "#2C3631",
  "control-border": "#7C8C84",
  rail: "#0B2019",
  "rail-ink": "#E8F0EA",
  "rail-muted": "#A9C2B6",
  "rail-hover": "#143528",
  accent: "#4FBF9A",
  "accent-hover": "#6FD3B2",
  "accent-ink": "#07231A",
  "ok-bg": "#12362B",
  "off-bg": "#262C29",
  danger: "#FF8F85",
  "danger-bg": "#3A1D1B",
  focus: "#7AD9BC",
};

describe("the Libro mayor design tokens", () => {
  it("defines every token of the theme on bare :root", () => {
    const { light } = readPlaces();

    for (const name of REQUIRED_TOKENS) {
      expect(light.get(name), name).toMatch(/^#[0-9a-fA-F]{6}$/);
    }
    expect(light.size).toBe(REQUIRED_TOKENS.length);
  });

  it("declares the light color-scheme on :root", () => {
    const css = readFileSync(join(process.cwd(), "src/app/globals.css"), "utf8");
    const body = ruleBody(css, /^:root \{/m) as string;

    expect(matchingScheme(body, "light")).toBe(true);
  });

  it("keeps the WCAG contrast of every checked light pair", () => {
    const { light } = readPlaces();

    for (const [foreground, background, minimum] of REQUIRED_CONTRAST) {
      const fg = light.get(foreground);
      const bg = light.get(background);
      expect(fg, `token ${foreground}`).toBeDefined();
      expect(bg, `token ${background}`).toBeDefined();
      const ratio = contrastRatio(fg as string, bg as string);
      expect(ratio, `${foreground}/${background}: ${ratio.toFixed(2)}`)
        .toBeGreaterThanOrEqual(minimum);
    }
  });
});

describe("the dark places of the theme", () => {
  it("declares the dark color-scheme in both places", () => {
    const css = readFileSync(join(process.cwd(), "src/app/globals.css"), "utf8");
    const system = ruleBody(
      css,
      /:root:not\(\[data-theme="light"\]\) \{/,
    ) as string;
    const explicit = ruleBody(css, /^:root\[data-theme="dark"\] \{/m) as string;

    expect(matchingScheme(system, "dark")).toBe(true);
    expect(matchingScheme(explicit, "dark")).toBe(true);
  });

  it("redefines every :root token in both dark places with the same value", () => {
    const { systemDark, explicitDark } = readPlaces();

    for (const name of REQUIRED_TOKENS) {
      expect(systemDark.get(name), `${name} in the media block`).toBeDefined();
      expect(explicitDark.get(name), `${name} in the attribute block`)
        .toBeDefined();
      expect(
        systemDark.get(name) === explicitDark.get(name),
        `${name} differs between the dark places`,
      ).toBe(true);
    }
  });

  it("uses the fixed dark values in both places", () => {
    const { systemDark, explicitDark } = readPlaces();

    for (const [name, value] of Object.entries(DARK_TOKENS)) {
      expect(systemDark.get(name), `${name} in the media block`).toBe(value);
      expect(explicitDark.get(name), `${name} in the attribute block`)
        .toBe(value);
    }
  });

  it("keeps the WCAG contrast of every checked dark pair", () => {
    const { systemDark, explicitDark } = readPlaces();

    for (const dark of [systemDark, explicitDark]) {
      for (const [foreground, background, minimum] of REQUIRED_DARK_CONTRAST) {
        const fg = dark.get(foreground);
        const bg = dark.get(background);
        expect(fg, `token ${foreground}`).toBeDefined();
        expect(bg, `token ${background}`).toBeDefined();
        const ratio = contrastRatio(fg as string, bg as string);
        expect(ratio, `${foreground}/${background}: ${ratio.toFixed(2)}`)
          .toBeGreaterThanOrEqual(minimum);
      }
    }
  });
});
