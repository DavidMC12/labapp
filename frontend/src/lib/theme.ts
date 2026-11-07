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

/**
 * Stores the explicit choices; "system" removes the key. Never throws:
 * with blocked storage the visit keeps the attribute it already has.
 */
export function writeStoredTheme(setting: ThemeSetting): void {
  try {
    if (setting === "system") {
      window.localStorage.removeItem(THEME_STORAGE_KEY);
    } else {
      window.localStorage.setItem(THEME_STORAGE_KEY, setting);
    }
  } catch {
    // Storage is blocked or full; the attribute is still applied.
  }
}

/**
 * The setting in force right now: the stored choice, else "system". The
 * selector calls it after hydration, never during render, so the server
 * and the client markup match.
 */
export function currentThemeSetting(): ThemeSetting {
  return readStoredTheme() ?? "system";
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

/**
 * The inline script of the root layout, started before the first paint:
 * it reads the stored choice and sets the attribute only for the two
 * explicit choices ("system" is no attribute, so the unlayered CSS
 * keyword of the media query applies). All inside try/catch, so blocked
 * cookies or storage leave the document on the system theme. Kept as a
 * constant so a test can assert exactly what ships in the HTML.
 */
export const THEME_INIT_SCRIPT =
  'try{var t=localStorage.getItem("labapp-theme");'
  + 'if(t==="light"||t==="dark"){document.documentElement.setAttribute("data-theme",t)}}catch(e){}';
