import {
  applyTheme,
  currentThemeSetting,
  readStoredTheme,
  THEME_INIT_SCRIPT,
  THEME_STORAGE_KEY,
  writeStoredTheme,
} from "./theme";
import { afterEach, describe, expect, it, vi } from "vitest";

/** A storage method that throws, as blocked storage does. */
function throwing(): never {
  throw new Error("blocked");
}

afterEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
});

describe("readStoredTheme", () => {
  it("returns the stored explicit choice", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "dark");

    expect(readStoredTheme()).toBe("dark");
  });

  it("returns null when nothing is stored", () => {
    expect(readStoredTheme()).toBeNull();
  });

  it("returns null for an unknown stored value", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "sepia");

    expect(readStoredTheme()).toBeNull();
  });

  it("returns null instead of throwing when the storage is blocked", () => {
    vi.spyOn(window.localStorage, "getItem").mockImplementation(throwing);

    expect(readStoredTheme()).toBeNull();
  });
});

describe("writeStoredTheme", () => {
  it("stores the explicit choices under the known key", () => {
    writeStoredTheme("light");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");

    writeStoredTheme("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });

  it("stores nothing for system", () => {
    writeStoredTheme("system");

    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBeNull();
  });

  it("removes the key when the choice goes back to system", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "dark");
    writeStoredTheme("system");

    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBeNull();
  });

  it("does not throw when the storage is blocked", () => {
    vi.spyOn(window.localStorage, "setItem").mockImplementation(throwing);
    vi.spyOn(window.localStorage, "removeItem").mockImplementation(throwing);

    expect(() => writeStoredTheme("dark")).not.toThrow();
    expect(() => writeStoredTheme("system")).not.toThrow();
  });
});

describe("currentThemeSetting", () => {
  it("falls back to system when nothing is stored", () => {
    expect(currentThemeSetting()).toBe("system");
  });

  it("returns the stored choice", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "light");

    expect(currentThemeSetting()).toBe("light");
  });
});

describe("applyTheme", () => {
  it("sets the data-theme attribute for the explicit choices", () => {
    applyTheme("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");

    applyTheme("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("removes the attribute for system", () => {
    document.documentElement.setAttribute("data-theme", "light");
    applyTheme("system");

    expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
  });
});

describe("THEME_INIT_SCRIPT", () => {
  it("reads exactly the storage key of this module", () => {
    expect(THEME_INIT_SCRIPT).toContain(THEME_STORAGE_KEY);
  });

  it("sets data-theme only for light and dark", () => {
    // The attribute happens inside the guard, so an unknown value never
    // reaches setAttribute.
    expect(THEME_INIT_SCRIPT).toContain('if(t==="light"||t==="dark")');
    expect(THEME_INIT_SCRIPT).toContain('setAttribute("data-theme",t)');
  });

  it("runs entirely inside one try/catch", () => {
    expect(THEME_INIT_SCRIPT.startsWith("try{")).toBe(true);
    expect(THEME_INIT_SCRIPT.endsWith("}catch(e){}")).toBe(true);
  });
});
