import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import LoginPage from "./page";
import { DEMO_USERS } from "@/features/auth/demo";

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

function jsonResponse(
  body: string,
  status: number,
  contentType = "application/problem+json",
) {
  return new Response(body, {
    status,
    headers: { "content-type": contentType },
  });
}

function deferredResponse(): {
  promise: Promise<Response>;
  respond: (response: Response) => void;
} {
  let respond!: (response: Response) => void;
  const promise = new Promise<Response>((resolve) => {
    respond = resolve;
  });
  return { promise, respond };
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
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
});

describe("login page structure", () => {
  it("renders heading, fields, submit button and demo box", () => {
    renderLoginPage();

    expect(
      screen.getByRole("heading", { name: "Iniciar sesión" }),
    ).toHaveAttribute("data-testid", "auth-login-heading");
    expect(screen.getByLabelText("Email")).toHaveAttribute("type", "email");
    expect(screen.getByLabelText("Email")).toHaveAttribute(
      "autocomplete",
      "username",
    );
    expect(screen.getByLabelText("Contraseña")).toHaveAttribute(
      "type",
      "password",
    );
    expect(screen.getByLabelText("Contraseña")).toHaveAttribute(
      "autocomplete",
      "current-password",
    );
    expect(
      screen.getByRole("button", { name: "Ingresar" }),
    ).toHaveAttribute("data-testid", "auth-login-submit-button");

    const form = document.querySelector("form");
    expect(form).toHaveAttribute("data-testid", "auth-login-form");
    expect(form).toHaveAttribute("novalidate");

    expect(
      screen.getByText("Usuarios de demostración"),
    ).toHaveAttribute("data-testid", "auth-login-demo-title-text");
    // SEED order: admin, sales, finance, readonly.
    DEMO_USERS.forEach((user, index) => {
      const item = screen.getByTestId(`auth-login-demo-item-${index + 1}`);
      expect(item).toHaveTextContent(user.email);
      expect(item).toHaveTextContent("· ");
    });
    expect(screen.getByTestId("auth-login-demo-password-text"))
      .toHaveTextContent("Contraseña para todos: Demo-LabApp-2026!");
  });
});

describe("login page validation", () => {
  it("shows required errors on empty fields without sending anything", async () => {
    renderLoginPage();
    const user = userEvent.setup();

    await user.click(screen.getByTestId("auth-login-submit-button"));

    expect(screen.getByTestId("auth-login-email-error")).toHaveTextContent(
      "Este campo es obligatorio.",
    );
    expect(
      screen.getByTestId("auth-login-password-error"),
    ).toHaveTextContent("Este campo es obligatorio.");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("ignores a whitespace-only email but checks the password as typed", async () => {
    renderLoginPage();
    const user = userEvent.setup();

    await user.type(screen.getByTestId("auth-login-email-input"), "   ");
    await user.type(
      screen.getByTestId("auth-login-password-input"),
      "Demo-LabApp-2026!",
    );
    await user.click(screen.getByTestId("auth-login-submit-button"));

    expect(screen.getByTestId("auth-login-email-error")).toHaveTextContent(
      "Este campo es obligatorio.",
    );
    expect(
      screen.queryByTestId("auth-login-password-error"),
    ).not.toBeInTheDocument();
  });

  it("sends the email trimmed and clears the previous errors", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        JSON.stringify({
          id: 1,
          name: "Admin Demo",
          email: "admin@labapp.test",
          role: "admin",
        }),
        200,
        "application/json",
      ),
    );
    renderLoginPage();
    const user = userEvent.setup();

    await user.click(screen.getByTestId("auth-login-submit-button"));
    expect(screen.getByTestId("auth-login-email-error")).toBeInTheDocument();

    await user.type(screen.getByTestId("auth-login-email-input"), " admin@labapp.test ");
    await user.type(
      screen.getByTestId("auth-login-password-input"),
      "Demo-LabApp-2026!",
    );
    await user.click(screen.getByTestId("auth-login-submit-button"));

    await waitFor(() => expect(routerMock.replace).toHaveBeenCalledWith("/"));

    expect(queryClient.getQueryData(["auth", "me"])).toMatchObject({
      email: "admin@labapp.test",
    });

    const [, init] = fetchMock.mock.calls[0] as [
      string,
      { body: string },
    ];
    expect(JSON.parse(init.body)).toEqual({
      email: "admin@labapp.test",
      password: "Demo-LabApp-2026!",
    });

    expect(
      screen.queryByTestId("auth-login-email-error"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("auth-login-password-error"),
    ).not.toBeInTheDocument();
  });
});

describe("login page failures", () => {
  const problem = (
    body: Record<string, unknown>,
    status: number,
  ) => jsonResponse(JSON.stringify(body), status);

  it("maps server 422 field errors to their fields", async () => {
    fetchMock.mockResolvedValue(
      problem(
        {
          status: 422,
          code: "VALIDATION_ERROR",
          detail: "Revisa los datos ingresados.",
          errors: [
            {
              field: "email",
              code: "INVALID_FORMAT",
              message: "El formato no es válido.",
            },
          ],
        },
        422,
      ),
    );
    renderLoginPage();
    const user = userEvent.setup();

    await user.type(
      screen.getByTestId("auth-login-email-input"),
      "admin@labapp.test",
    );
    await user.type(
      screen.getByTestId("auth-login-password-input"),
      "wrong-password",
    );
    await user.click(screen.getByTestId("auth-login-submit-button"));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    expect(screen.getByTestId("auth-login-email-error")).toHaveTextContent(
      "El formato no es válido.",
    );
    expect(screen.queryByRole("alert")).toHaveAttribute(
      "data-testid",
      "auth-login-email-error",
    );
  });

  it("shows unmatched problems in the form-level alert and focuses it", async () => {
    fetchMock.mockResolvedValue(
      problem(
        {
          status: 401,
          code: "INVALID_CREDENTIALS",
          detail: "Email o contraseña incorrectos.",
        },
        401,
      ),
    );
    renderLoginPage();
    const user = userEvent.setup();

    await user.type(
      screen.getByTestId("auth-login-email-input"),
      "admin@labapp.test",
    );
    await user.type(
      screen.getByTestId("auth-login-password-input"),
      "wrong-password",
    );
    await user.click(screen.getByTestId("auth-login-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("auth-login-form-alert")).toHaveTextContent(
        "Email o contraseña incorrectos.",
      );
    });

    expect(document.activeElement).toHaveAttribute(
      "data-testid",
      "auth-login-form-alert",
    );
    expect(routerMock.replace).not.toHaveBeenCalled();
  });

  it("maps a network failure to the form-level alert and focuses it", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
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
      expect(screen.getByTestId("auth-login-form-alert")).toHaveTextContent(
        "Ocurrió un error inesperado. Inténtalo de nuevo.",
      );
    });
    expect(document.activeElement).toHaveAttribute(
      "data-testid",
      "auth-login-form-alert",
    );
  });

  it("focuses the first field with an error when the alert is not shown", async () => {
    // Only the password fails server-side validation.
    fetchMock.mockResolvedValue(
      problem(
        {
          status: 422,
          code: "VALIDATION_ERROR",
          detail: "Revisa los datos ingresados.",
          errors: [
            {
              field: "password",
              code: "TOO_SHORT",
              message: "Debe tener al menos 8 caracteres.",
            },
          ],
        },
        422,
      ),
    );
    renderLoginPage();
    const user = userEvent.setup();

    await user.type(
      screen.getByTestId("auth-login-email-input"),
      "admin@labapp.test",
    );
    await user.type(screen.getByTestId("auth-login-password-input"), "wrong");
    await user.click(screen.getByTestId("auth-login-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("auth-login-password-error"))
        .toHaveTextContent("Debe tener al menos 8 caracteres.");
    });

    expect(document.activeElement).toHaveAttribute(
      "data-testid",
      "auth-login-password-input",
    );
  });

  it("ignores a second submit while one is pending", async () => {
    const { promise, respond } = deferredResponse();
    fetchMock.mockReturnValueOnce(promise);
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

    // The first submit puts the button in the loading state.
    await user.click(screen.getByTestId("auth-login-submit-button"));
    const submitButton = screen.getByTestId("auth-login-submit-button");
    expect(submitButton).toHaveTextContent("Ingresando…");
    expect(submitButton).toHaveAttribute("data-state", "loading");
    expect(submitButton).toHaveAttribute("aria-busy", "true");
    expect(submitButton).toBeDisabled();

    // Even a submit dispatched straight to the form, bypassing the
    // disabled button, is ignored by the handler guard.
    const form = document.querySelector(
      "[data-testid='auth-login-form']",
    ) as HTMLFormElement;
    form.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    respond(
      jsonResponse(
        JSON.stringify({
          id: 1,
          name: "Admin Demo",
          email: "admin@labapp.test",
          role: "admin",
        }),
        200,
        "application/json",
      ),
    );
    await waitFor(() => {
      expect(routerMock.replace).toHaveBeenCalledWith("/");
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
