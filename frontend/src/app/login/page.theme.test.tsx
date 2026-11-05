import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import LoginPage from "./page";
import { isValidTestId } from "@/lib/testid";

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
  usePathname: () => "/",
}));

function renderLoginPage() {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <LoginPage />
    </QueryClientProvider>,
  );
}

describe("the login theme pieces", () => {
  it("shows the tagline of the rail panel", () => {
    renderLoginPage();

    expect(screen.getByTestId("auth-login-tagline-text")).toHaveTextContent(
      "Del pedido al cobro, sin perder el hilo.",
    );
  });

  it("shows the demo notice under the tagline", () => {
    renderLoginPage();

    expect(screen.getByTestId("auth-login-notice-text")).toHaveTextContent(
      "Demostración pública. Los datos se reinician cada noche.",
    );
  });

  it("keeps the new text ids valid test ids", () => {
    for (const id of ["auth-login-tagline-text", "auth-login-notice-text"]) {
      expect(isValidTestId(id), id).toBe(true);
    }
  });
});
