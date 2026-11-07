"use client";

import { Select } from "./Select";
import {
  subscribeToThemeChanges,
  applyTheme,
  currentThemeSetting,
  writeStoredTheme,
  themeServerSetting,
  type ThemeSetting,
} from "@/lib/theme";
import type { ChangeEvent } from "react";
import { useSyncExternalStore } from "react";
import type { TestId } from "@/lib/testid";

type ThemeSelectProps = {
  id: string;
  testId: TestId;
};

/**
 * The "Tema" control of the theme (task 023): "Sistema" is the default
 * and follows the browser preference, "Claro" and "Oscuro" pin the theme
 * by writing `data-theme` on `<html>` and remembering the choice under
 * the storage key of `src/lib/theme.ts`.
 *
 * The setting comes from the external store of `src/lib/theme.ts` with
 * `useSyncExternalStore`: during hydration the server snapshot ("system",
 * what the server markup shows) applies, and the real stored choice takes
 * over right after, never during a render. With blocked storage every
 * operation degrades silently to the system theme.
 */
export function ThemeSelect({ id, testId }: ThemeSelectProps) {
  const setting = useSyncExternalStore(
    subscribeToThemeChanges,
    currentThemeSetting,
    themeServerSetting,
  );

  function handleChange(event: ChangeEvent<HTMLSelectElement>) {
    const next = event.target.value as ThemeSetting;
    applyTheme(next);
    writeStoredTheme(next);
  }

  return (
    <Select
      id={id}
      testId={testId}
      label="Tema"
      value={setting}
      onChange={handleChange}
    >
      <option value="system">Sistema</option>
      <option value="light">Claro</option>
      <option value="dark">Oscuro</option>
    </Select>
  );
}
