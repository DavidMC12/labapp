"use client";

import { Select } from "./Select";
import {
  applyTheme,
  currentThemeSetting,
  writeStoredTheme,
  type ThemeSetting,
} from "@/lib/theme";
import type { ChangeEvent } from "react";
import { useEffect, useState } from "react";
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
 * The stored choice is read after hydration, never during render, so the
 * server and the client markup match ("system" is what a fresh render
 * shows when nothing is stored yet). With blocked storage every
 * operation degrades silently to the system theme.
 */
export function ThemeSelect({ id, testId }: ThemeSelectProps) {
  const [setting, setSetting] = useState<ThemeSetting>("system");

  useEffect(() => {
    setSetting(currentThemeSetting());
  }, []);

  function handleChange(event: ChangeEvent<HTMLSelectElement>) {
    const next = event.target.value as ThemeSetting;
    setSetting(next);
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
