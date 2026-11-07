import {
  applyTheme,
  currentThemeSetting,
  readStoredTheme,
  subscribeToThemeChanges,
  themeServerSetting,
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

describe("subscribeToThemeChanges", () => {
  it("notifies the subscribers of a local write and of a storage event", () => {
    const notify = vi.fn();
    const unsubscribe = subscribeToThemeChanges(notify);

    writeStoredTheme("dark");
    expect(notify).toHaveBeenCalledTimes(1);

    window.dispatchEvent(new StorageEvent("storage"));
    expect(notify).toHaveBeenCalledTimes(2);

    unsubscribe();

    writeStoredTheme("light");
    window.dispatchEvent(new StorageEvent("storage"));
    expect(notify).toHaveBeenCalledTimes(2);
  });
});

describe("themeServerSetting", () => {
  it("is always system: the server never sees the client storage", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "dark");

    expect(themeServerSetting()).toBe("system");
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

// The script assertions live next to the layout that ships it:
// src/app/layout.test.tsx.
