import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import LoginPage from "./page";

const { routerMock, navState } = vi.hoisted(() => ({
  routerMock: {
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  },
  navState: { search: "" },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => routerMock,
  useSearchParams: () => new URLSearchParams(navState.search),
}));

const fetchMock = vi.fn();

let queryClient: QueryClient;

function renderLoginPage() {
  render(
    <QueryClientProvider client={queryClient}>
      <LoginPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  navState.search = "";
  routerMock.replace.mockClear();
  queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  navState.search = "";
});

const successResponse = () =>
  new Response(
    JSON.stringify({
      id: 1,
      name: "Admin Demo",
      email: "admin@labapp.test",
      role: "admin",
    }),
    { status: 200, headers: { "content-type": "application/json" } },
  );

describe("the expired session notice of the login page", () => {
  it("is absent without the expired parameter", () => {
    renderLoginPage();

    expect(screen.queryByTestId("auth-login-expired-alert"))
      .not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Iniciar sesión" }))
      .toBeInTheDocument();
  });

  it("shows the alert above the form when the url has expired=1", () => {
    navState.search = "expired=1";
    renderLoginPage();

    const notice = screen.getByTestId("auth-login-expired-alert");
    expect(notice).toHaveTextContent(
      "Tu sesión expiró. Inicia sesión de nuevo.",
    );
    expect(notice).toHaveAttribute("role", "alert");

    // It sits above the form in the DOM, and the demo credentials box is
    // still there.
    const form = screen.getByTestId("auth-login-form");
    expect(notice.compareDocumentPosition(form))
      .toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    expect(screen.getByTestId("auth-login-demo-list")).toBeInTheDocument();
    expect(screen.getByTestId("auth-login-demo-password-text"))
      .toBeInTheDocument();
  });

  it("disappears after a successful login", async () => {
    navState.search = "expired=1";
    fetchMock.mockResolvedValue(successResponse());
    renderLoginPage();
    const user = userEvent.setup();

    await user.type(
      screen.getByTestId("auth-login-email-input"),
      "admin@labapp.test",
    );
    await user.type(
      screen.getByTestId("auth-login-password-input"),
      "Demo-LabApp-2026!",
    );
    await user.click(screen.getByTestId("auth-login-submit-button"));

    await waitFor(() => {
      expect(routerMock.replace).toHaveBeenCalledWith("/");
    });
    expect(screen.queryByTestId("auth-login-expired-alert"))
      .not.toBeInTheDocument();
  });
});
