import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * The tokens of the "Libro mayor" theme are read back from globals.css,
 * so the test verifies the file the app really ships and fails if a value
 * is edited without checking its contrast again.
 *
 * The file is parsed block by block with a brace counter: the media place
 * nests the `:root:not([data-theme="light"])` rule inside the
 * `@media (prefers-color-scheme: dark)` block, so a plain global regex
 * would keep only the last declaration of each name and silently test the
 * dark values for everyone.
 */

type ColorName = string;
type TokenBlock = Map<ColorName, string>;

const CSS_PATH = join(process.cwd(), "src/app/globals.css");

/**
 * The body of the rule that starts at the given selector match, counted
 * with a brace depth from the opening `{`: nested blocks (the @media
 * block) are handled and the body ends at the matching `}`.
 */
function extractRuleBody(css: string, selector: RegExp): string | null {
  const match = selector.exec(css);
  if (!match) {
    return null;
  }
  const open = css.indexOf("{", match.index);
  if (open === -1) {
    return null;
  }
  let depth = 0;
  for (let index = open; index < css.length; index++) {
    const character = css[index];
    if (character === "{") {
      depth++;
    } else if (character === "}") {
      depth--;
      if (depth === 0) {
        return css.slice(open + 1, index);
      }
    }
  }
  return null;
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

/** Whether the rule body declares the given `color-scheme` value. */
function matchingScheme(body: string, scheme: string): boolean {
  return new RegExp(`color-scheme:\\s*${scheme}\\s*;`).test(body);
}

const ROOT_SELECTOR = /^:root \{/m;
const SYSTEM_DARK_SELECTOR = /:root:not\(\[data-theme="light"\]\) \{/;
const EXPLICIT_DARK_SELECTOR = /^:root\[data-theme="dark"\] \{/m;

function readPlaces(): {
  light: TokenBlock;
  systemDark: TokenBlock;
  explicitDark: TokenBlock;
} {
  const css = readFileSync(CSS_PATH, "utf8");
  const light = extractRuleBody(css, ROOT_SELECTOR);
  const systemDark = extractRuleBody(css, SYSTEM_DARK_SELECTOR);
  const explicitDark = extractRuleBody(css, EXPLICIT_DARK_SELECTOR);

  expect(light, "the bare :root block").not.toBeNull();
  expect(systemDark, "the dark media query block").not.toBeNull();
  expect(explicitDark, "the data-theme dark block").not.toBeNull();

  return {
    light: parseTokens(light as string),
    systemDark: parseTokens(systemDark as string),
    explicitDark: parseTokens(explicitDark as string),
  };
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
  "rail-active",
  "rail-active-ink",
  "accent",
  "accent-hover",
  "accent-ink",
  "ok-bg",
  "off-bg",
  "danger",
  "danger-bg",
  "focus",
];

/** The light values, pinned exactly as they ship today. */
const LIGHT_TOKENS: Record<ColorName, string> = {
  paper: "#FBFAF6",
  surface: "#FFFFFF",
  ink: "#18241F",
  muted: "#5B6B63",
  line: "#D9D4C5",
  "control-border": "#8A8470",
  rail: "#14342B",
  "rail-ink": "#E8F0EA",
  "rail-muted": "#A9C2B6",
  "rail-hover": "#1D4A3D",
  "rail-active": "#FBFAF6",
  "rail-active-ink": "#18241F",
  accent: "#0F5B46",
  "accent-hover": "#0B4A38",
  "accent-ink": "#FFFFFF",
  "ok-bg": "#DCEBE3",
  "off-bg": "#ECE9DF",
  danger: "#A3261B",
  "danger-bg": "#F9E1DE",
  focus: "#1F8A6C",
};

/** The dark values, exactly as the brief fixes them. */
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
  "rail-active": "#24573F",
  "rail-active-ink": "#E8F0EA",
  accent: "#4FBF9A",
  "accent-hover": "#6FD3B2",
  "accent-ink": "#07231A",
  "ok-bg": "#12362B",
  "off-bg": "#262C29",
  danger: "#FF8F85",
  "danger-bg": "#3A1D1B",
  focus: "#7AD9BC",
};

/** Every checked pair, minimums included, run for both themes. */
const REQUIRED_CONTRAST: [foreground: string, background: string, minimum: number][] = [
  ["ink", "paper", 4.5],
  ["ink", "surface", 4.5],
  ["muted", "paper", 4.5],
  ["muted", "surface", 4.5],
  ["rail-ink", "rail", 4.5],
  ["rail-ink", "rail-hover", 4.5],
  ["rail-muted", "rail", 4.5],
  ["rail-muted", "rail-hover", 4.5],
  ["rail-active-ink", "rail-active", 4.5],
  ["accent-ink", "accent", 4.5],
  ["accent-ink", "accent-hover", 4.5],
  ["accent", "ok-bg", 4.5],
  ["muted", "off-bg", 4.5],
  ["danger", "danger-bg", 4.5],
  ["danger", "paper", 4.5],
  ["danger", "surface", 4.5],
  ["accent", "paper", 4.5],
  ["accent", "surface", 4.5],
  ["control-border", "surface", 3],
  ["control-border", "paper", 3],
  ["focus", "paper", 3],
  ["focus", "surface", 3],
  ["focus", "rail", 3],
];

describe("the Libro mayor design tokens", () => {
  it("defines every token of the theme on bare :root with the pinned light values", () => {
    const { light } = readPlaces();

    for (const name of REQUIRED_TOKENS) {
      expect(light.get(name), name).toBe(LIGHT_TOKENS[name]);
    }
    expect(light.size).toBe(REQUIRED_TOKENS.length);
  });

  it("declares the light color-scheme on :root", () => {
    const rootBody = extractRuleBody(
      readFileSync(CSS_PATH, "utf8"),
      ROOT_SELECTOR,
    ) as string;

    expect(matchingScheme(rootBody, "light")).toBe(true);
  });

  it("keeps the WCAG contrast of every checked pair in the light theme", () => {
    const { light } = readPlaces();

    for (const [foreground, background, minimum] of REQUIRED_CONTRAST) {
      const fg = light.get(foreground);
      const bg = light.get(background);
      expect(fg, `token ${foreground}`).toBeDefined();
      expect(bg, `token ${background}`).toBeDefined();
      const ratio = contrastRatio(fg as string, bg as string);
      expect(ratio, `light ${foreground}/${background}: ${ratio.toFixed(2)}`)
        .toBeGreaterThanOrEqual(minimum);
    }
  });
});

describe("the dark places of the theme", () => {
  it("declares the dark color-scheme in both places", () => {
    const css = readFileSync(CSS_PATH, "utf8");
    const system = extractRuleBody(css, SYSTEM_DARK_SELECTOR) as string;
    const explicit = extractRuleBody(css, EXPLICIT_DARK_SELECTOR) as string;

    expect(matchingScheme(system, "dark")).toBe(true);
    expect(matchingScheme(explicit, "dark")).toBe(true);
  });

  it("carries exactly every :root token in both dark places with the same value", () => {
    const { light, systemDark, explicitDark } = readPlaces();

    for (const name of REQUIRED_TOKENS) {
      expect(systemDark.get(name), `${name} in the media block`).toBeDefined();
      expect(explicitDark.get(name), `${name} in the attribute block`)
        .toBeDefined();
      expect(
        systemDark.get(name) === explicitDark.get(name),
        `${name} differs between the dark places`,
      ).toBe(true);
    }
    // No dark-only token may exist: the shape of the theme is the token
    // list, always defined first on bare :root.
    for (const name of systemDark.keys()) {
      expect(light.has(name), `${name} exists only in the media block`).toBe(
        true,
      );
    }
    for (const name of explicitDark.keys()) {
      expect(
        light.has(name),
        `${name} exists only in the attribute block`,
      ).toBe(true);
    }
  });

  it("uses the fixed dark values in both places", () => {
    const { systemDark, explicitDark } = readPlaces();

    for (const dark of [systemDark, explicitDark]) {
      for (const [name, value] of Object.entries(DARK_TOKENS)) {
        expect(dark.get(name), `${name}`).toBe(value);
      }
      expect(dark.size).toBe(REQUIRED_TOKENS.length);
    }
  });

  it("keeps the WCAG contrast of every checked pair in the dark theme", () => {
    const { systemDark, explicitDark } = readPlaces();

    for (const dark of [systemDark, explicitDark]) {
      for (const [foreground, background, minimum] of REQUIRED_CONTRAST) {
        const fg = dark.get(foreground);
        const bg = dark.get(background);
        expect(fg, `token ${foreground}`).toBeDefined();
        expect(bg, `token ${background}`).toBeDefined();
        const ratio = contrastRatio(fg as string, bg as string);
        expect(
          ratio,
          `dark ${foreground}/${background}: ${ratio.toFixed(2)}`,
        ).toBeGreaterThanOrEqual(minimum);
      }
    }
  });
});
