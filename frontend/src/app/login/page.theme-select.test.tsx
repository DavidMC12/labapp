import LoginPage from "./page";
import { ThemeSelect } from "@/components/ui";
import { THEME_STORAGE_KEY } from "@/lib/theme";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { renderToStaticMarkup } from "react-dom/server";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

const { routerMock } = vi.hoisted(() => ({
  routerMock: {
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => routerMock,
  usePathname: () => "/login",
  useSearchParams: () => new URLSearchParams(),
}));

afterEach(() => {
  window.localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  vi.restoreAllMocks();
});

function wrappers(children: ReactNode) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      {children}
    </QueryClientProvider>
  );
}

describe("the theme of the login page", () => {
  it("offers the Tema control at the top of the form column", async () => {
    render(wrappers(<LoginPage />));

    const heading = screen.getByTestId("auth-login-heading");
    const selector = screen.getByTestId(
      "auth-login-theme-select",
    ) as HTMLSelectElement;

    expect(selector).toBeInTheDocument();
    // The selector renders above the heading in the DOM order.
    expect(
      heading.compareDocumentPosition(selector)
        & Node.DOCUMENT_POSITION_PRECEDING,
    ).toBeTruthy();

    const options = [...selector.options].map((option) => option.textContent);
    expect(options).toEqual(["Sistema", "Claro", "Oscuro"]);
  });

  it("renders system on the server markup even with a stored choice", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "dark");

    const markup = renderToStaticMarkup(
      wrappers(<ThemeSelect testId="auth-login-theme-select" id="auth-login-theme" />),
    );

    expect(markup).not.toMatch(/<option value="dark"[^>]*selected/);
    expect(markup).toMatch(/<option value="system"[^>]*selected/);
  });

  it("applies the choice of the user to the document", async () => {
    render(wrappers(<LoginPage />));
    const user = userEvent.setup();

    await user.selectOptions(screen.getByTestId("auth-login-theme-select"), "dark");

    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });
});
