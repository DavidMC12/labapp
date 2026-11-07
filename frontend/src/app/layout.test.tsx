import RootLayout, { THEME_NO_FLASH_SCRIPT } from "./layout";
import { THEME_STORAGE_KEY } from "@/lib/theme";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { ReactElement, ReactNode } from "react";

/**
 * next/font/google would try to fetch fonts at import time; the layout
 * test only needs the class variables.
 */
vi.mock("next/font/google", () => ({
  IBM_Plex_Sans: () => ({ className: "", variable: "--font-plex-sans" }),
  IBM_Plex_Serif: () => ({ className: "", variable: "--font-plex-serif" }),
}));

// The tokens file does not survive the unit-test PostCSS chain; the
// tokens.test.ts covers it by reading the file.
vi.mock("./globals.css", () => ({}));

function rootLayoutMarkup(children: ReactNode): string {
  return renderToStaticMarkup(<RootLayout>{children}</RootLayout>);
}

describe("the root layout theme", () => {
  it("puts the no-flash script into the head", () => {
    const markup = rootLayoutMarkup(<p>página</p>);

    const head = markup.slice(0, markup.indexOf("</head>"));
    const script = /<script>([\s\S]*?)<\/script>/.exec(head);

    expect(script).not.toBeNull();
  });

  it("ships the inline script text verbatim", () => {
    const markup = rootLayoutMarkup(<p>página</p>);

    const head = markup.slice(0, markup.indexOf("</head>"));
    const script = /<script>([\s\S]*?)<\/script>/.exec(head);

    expect(script?.[1]).toBe(THEME_NO_FLASH_SCRIPT);
  });

  it("keeps the script reading the storage key of the theme module", () => {
    expect(THEME_NO_FLASH_SCRIPT).toContain(THEME_STORAGE_KEY);
  });

  it("sets data-theme only for light and dark", () => {
    // The attribute happens inside the guard, so an unknown value never
    // reaches setAttribute.
    expect(THEME_NO_FLASH_SCRIPT).toContain('if(t==="light"||t==="dark")');
    expect(THEME_NO_FLASH_SCRIPT).toContain('setAttribute("data-theme",t)');
  });

  it("wraps the storage access inside one try/catch", () => {
    expect(THEME_NO_FLASH_SCRIPT.startsWith("try{")).toBe(true);
    expect(THEME_NO_FLASH_SCRIPT.endsWith("}catch(e){}")).toBe(true);
  });

  it("reads the storage synchronously inside the try block", () => {
    const storageAccess = THEME_NO_FLASH_SCRIPT.indexOf(
      "window.localStorage.getItem",
    );
    const tryStart = THEME_NO_FLASH_SCRIPT.indexOf("try{");
    const catchStart = THEME_NO_FLASH_SCRIPT.indexOf("}catch(e){}");

    expect(storageAccess).toBeGreaterThan(tryStart);
    expect(storageAccess).toBeLessThan(catchStart);
  });

  it("suppresses the hydration warning on <html>", () => {
    // The script runs before hydration and may add data-theme, so React
    // must not warn about the client-side attribute of <html>. Rendering
    // drops internal flags, so call the function component directly.
    const tree = RootLayout({ children: <p>página</p> }) as ReactElement<{
      suppressHydrationWarning?: boolean;
      [key: string]: unknown;
    }>;

    expect(tree.type).toBe("html");
    expect(tree.props.suppressHydrationWarning).toBe(true);
  });

  it("exposes no data-theme on the server markup (system by default)", () => {
    const markup = rootLayoutMarkup(<p>página</p>);

    // The script string mentions data-theme; the attribute itself never
    // appears with no stored choice.
    expect(markup).not.toMatch(/\sdata-theme=/);
  });
});
