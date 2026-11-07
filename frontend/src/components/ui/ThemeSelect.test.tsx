import { ThemeSelect } from "./ThemeSelect";
import { THEME_STORAGE_KEY } from "@/lib/theme";
import { render, screen, waitFor } from "@testing-library/react";
import { renderToStaticMarkup } from "react-dom/server";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  window.localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  vi.restoreAllMocks();
});

function renderSelector() {
  return render(
    <ThemeSelect id="theme-select" testId="app-theme-select" />,
  );
}

describe("the theme selector", () => {
  it("shows the three choices with system selected at first", () => {
    renderSelector();

    const select = screen.getByTestId(
      "app-theme-select",
    ) as HTMLSelectElement;
    expect(select.value).toBe("system");

    const options = [...select.options].map((option) => option.textContent);
    expect(options).toEqual(["Sistema", "Claro", "Oscuro"]);
  });

  it("renders the system choice on the server markup even with a stored choice", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "light");

    // Static markup is what the server sends; it must not depend on the
    // storage of the client, so the selector corrects itself only after
    // hydration (next test).
    const markup = renderToStaticMarkup(
      <ThemeSelect id="theme-select" testId="app-theme-select" />,
    );

    expect(markup).not.toMatch(/<option value="light"[^>]*selected/);
    expect(markup).toMatch(/<option value="system"[^>]*selected/);
  });

  it("takes the stored choice after hydration", async () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "light");

    renderSelector();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(
        (screen.getByTestId("app-theme-select") as HTMLSelectElement).value,
      ).toBe("light");
    });

    // Hydration read only: choosing the same value again is still a
    // normal user action afterwards.
    await user.selectOptions(screen.getByTestId("app-theme-select"), "light");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
  });

  it("applies and stores dark when the user chooses Oscuro", async () => {
    renderSelector();
    const user = userEvent.setup();

    await user.selectOptions(screen.getByTestId("app-theme-select"), "dark");

    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    // The store write re-renders the controlled select after the change.
    await waitFor(() => {
      expect(
        (screen.getByTestId("app-theme-select") as HTMLSelectElement).value,
      ).toBe("dark");
    });
  });

  it("applies and stores light when the user chooses Claro", async () => {
    renderSelector();
    const user = userEvent.setup();

    await user.selectOptions(screen.getByTestId("app-theme-select"), "light");

    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
  });

  it("removes the attribute and the key when the user returns to Sistema", async () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "dark");
    document.documentElement.setAttribute("data-theme", "dark");
    renderSelector();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(
        (screen.getByTestId("app-theme-select") as HTMLSelectElement).value,
      ).toBe("dark");
    });

    await user.selectOptions(screen.getByTestId("app-theme-select"), "system");

    expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBeNull();
  });

  it("keeps working when the storage is blocked", async () => {
    vi.spyOn(window.localStorage, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(window.localStorage, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(window.localStorage, "removeItem").mockImplementation(() => {
      throw new Error("blocked");
    });

    renderSelector();
    const user = userEvent.setup();

    // Reading stays on system.
    await waitFor(() => {
      expect(
        (screen.getByTestId("app-theme-select") as HTMLSelectElement).value,
      ).toBe("system");
    });

    // Choosing still applies the attribute instead of breaking the page.
    await user.selectOptions(screen.getByTestId("app-theme-select"), "dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });
});
