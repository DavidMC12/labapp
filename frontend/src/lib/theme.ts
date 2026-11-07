/**
 * The theme of the app. The setting lives in `localStorage` under
 * `THEME_STORAGE_KEY`; the visible theme comes from the `data-theme`
 * attribute of `<html>` and the token blocks of `globals.css`:
 *
 * - no attribute (the "system" setting): the CSS follows the browser
 *   preference through `@media (prefers-color-scheme: dark)`;
 * - `data-theme="light"` / `data-theme="dark"`: the explicit choice of the
 *   user, which wins over the system preference.
 *
 * Everything that touches `localStorage` is inside try/catch: in private
 * windows or with blocked storage the functions degrade to the system
 * theme instead of breaking the page.
 */

export const THEME_STORAGE_KEY = "labapp-theme";

/** What the selector holds: the two stored choices, or "system". */
export type ThemeSetting = "system" | "light" | "dark";

/** The values allowed inside the storage (only the explicit choices). */
export type StoredTheme = "light" | "dark";

function isStoredTheme(value: unknown): value is StoredTheme {
  return value === "light" || value === "dark";
}

/**
 * The stored explicit choice, or `null` when nothing is stored, when the
 * value is unknown, or when reading fails (blocked storage).
 */
export function readStoredTheme(): StoredTheme | null {
  try {
    const value = window.localStorage.getItem(THEME_STORAGE_KEY);
    return isStoredTheme(value) ? value : null;
  } catch {
    return null;
  }
}

const storageListeners = new Set<() => void>();

/**
 * The external store of the theme, consumed by the selectors with
 * `useSyncExternalStore`: the `storage` event fires when another tab
 * changes the choice, and a write made in this tab (the only writer) is
 * followed by a notification of its own subscribers.
 */
export function subscribeToThemeChanges(notify: () => void): () => void {
  storageListeners.add(notify);
  window.addEventListener("storage", notify);
  return () => {
    storageListeners.delete(notify);
    window.removeEventListener("storage", notify);
  };
}

function notifyThemeChanged(): void {
  for (const notify of storageListeners) {
    notify();
  }
}

/**
 * Stores the explicit choices; "system" removes the key. Never throws:
 * with blocked storage the visit keeps the attribute it already has.
 * After a successful write the subscribers are notified, so the store
 * consumers re-render with the new snapshot.
 */
export function writeStoredTheme(setting: ThemeSetting): void {
  try {
    if (setting === "system") {
      window.localStorage.removeItem(THEME_STORAGE_KEY);
    } else {
      window.localStorage.setItem(THEME_STORAGE_KEY, setting);
    }
    notifyThemeChanged();
  } catch {
    // Storage is blocked or full; the attribute is still applied.
  }
}

/** The setting in force right now: the stored choice, else "system". */
export function currentThemeSetting(): ThemeSetting {
  return readStoredTheme() ?? "system";
}

/**
 * The setting the server markup always shows: "system", because the
 * server cannot see the `localStorage` of the client. The selector uses
 * it as the server snapshot of `useSyncExternalStore`, so the hydration
 * markup matches and the stored choice takes over after hydration.
 */
export function themeServerSetting(): ThemeSetting {
  return "system";
}

/**
 * Puts the attribute of the setting on `<html>`: `removeAttribute` for
 * "system", the value for an explicit choice. The CSS of globals.css
 * keys on exactly this attribute.
 */
export function applyTheme(setting: ThemeSetting): void {
  const root = document.documentElement;
  if (setting === "system") {
    root.removeAttribute("data-theme");
  } else {
    root.setAttribute("data-theme", setting);
  }
}
