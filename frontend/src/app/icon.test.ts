import { readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * The site icon (task 047) is served by the `icon.svg` file convention of
 * Next.js, which adds the `<link rel="icon">`. It must stay a plain, small
 * SVG mark: no script, no external reference, no text that would depend on
 * a font, and small enough to be reviewed by eye.
 */

/* Tests run with the frontend directory as the working directory. */
const PATH = join(process.cwd(), "src", "app", "icon.svg");
const SOURCE = readFileSync(PATH, "utf8");
const SIZE = statSync(PATH).size;

describe("the site icon", () => {
  it("parses as XML with a root svg element and a 32x32 viewBox", () => {
    const document = new DOMParser().parseFromString(SOURCE, "application/xml");
    expect(document.querySelector("parsererror")).toBeNull();
    expect(document.documentElement.tagName).toBe("svg");
    expect(document.documentElement.getAttribute("viewBox")).toBe("0 0 32 32");
  });

  it("carries no script, no external reference and no text", () => {
    expect(SOURCE).not.toMatch(/<script/i);
    expect(SOURCE).not.toMatch(/href=/i);
    expect(SOURCE).not.toMatch(/xlink:href/i);
    expect(SOURCE).not.toMatch(/<text/i);
    expect(SOURCE).not.toMatch(/url\(\s*http/i);
  });

  it("stays under one kilobyte", () => {
    expect(SIZE).toBeLessThan(1024);
  });
});
