import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CustomerForm } from "./CustomerForm";
import type { Customer } from "./types";

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

const customer: Customer = {
  id: 7,
  name: "Hotel Horizonte",
  email: "hotel@example.test",
  phone: null,
  tax_id: "HOTE-800123",
  address: "Paseo del Prado 15",
  status: "active",
  version: 3,
  created_at: "2026-01-01T09:07:00Z",
  updated_at: "2026-01-01T09:07:00Z",
};

function renderForm(
  props: Parameters<typeof CustomerForm>[0] = { mode: "create" },
) {
  render(
    <QueryClientProvider client={queryClient}>
      <CustomerForm {...props} />
    </QueryClientProvider>,
  );
}

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), { status });
}

function problem(body: Record<string, unknown>): Response {
  return jsonResponse(body, body.status as number);
}

const VALIDATION_PROBLEM = {
  status: 422,
  code: "VALIDATION_ERROR",
  detail: "Revisa los datos ingresados.",
};

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

describe("the customer form structure", () => {
  it("renders the create form with heading, fields, submit and cancel", () => {
    renderForm({ mode: "create" });

    expect(screen.getByRole("heading", { name: "Nuevo cliente" }))
      .toHaveAttribute("data-testid", "customers-form-heading");
    expect(screen.getByTestId("customers-customer-form"))
      .toHaveAttribute("novalidate");
    expect(screen.getByTestId("customers-form-name-input"))
      .toHaveAccessibleName("Nombre");
    expect(screen.getByTestId("customers-form-email-input"))
      .toHaveAttribute("type", "email");
    expect(screen.getByTestId("customers-form-email-input"))
      .toHaveAccessibleName("Email");
    expect(screen.getByTestId("customers-form-phone-input"))
      .toHaveAccessibleName("Teléfono");
    expect(screen.getByTestId("customers-form-taxid-input"))
      .toHaveAccessibleName("ID fiscal");
    expect(screen.getByTestId("customers-form-address-textarea"))
      .toHaveAccessibleName("Dirección");
    expect(screen.getByTestId("customers-form-submit-button"))
      .toHaveTextContent("Guardar");
    expect(screen.getByTestId("customers-form-cancel-link"))
      .toHaveAttribute("href", "/customers");
  });

  it("renders the edit form prefilled and pointed back at the detail", () => {
    renderForm({ mode: "edit", customer, resetSignal: 0, onReload: vi.fn() });

    expect(screen.getByRole("heading", { name: "Editar cliente" }))
      .toHaveAttribute("data-testid", "customers-form-heading");
    expect(screen.getByTestId("customers-form-name-input"))
      .toHaveValue("Hotel Horizonte");
    expect(screen.getByTestId("customers-form-email-input"))
      .toHaveValue("hotel@example.test");
    expect(screen.getByTestId("customers-form-phone-input")).toHaveValue("");
    expect(screen.getByTestId("customers-form-taxid-input"))
      .toHaveValue("HOTE-800123");
    expect(screen.getByTestId("customers-form-address-textarea"))
      .toHaveValue("Paseo del Prado 15");
    expect(screen.getByTestId("customers-form-cancel-link"))
      .toHaveAttribute("href", "/customers/7");
  });
});

describe("the customer form submit", () => {
  it("posts a create with null for empty optionals", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ ...customer, id: 11, name: "Nueva" }, 201),
    );
    renderForm({ mode: "create" });
    const user = userEvent.setup();

    await user.type(screen.getByTestId("customers-form-name-input"), "Nueva");
    await user.type(
      screen.getByTestId("customers-form-email-input"),
      "nueva@example.test",
    );
    await user.click(screen.getByTestId("customers-form-submit-button"));

    await waitFor(() => expect(routerMock.replace).toHaveBeenCalledWith("/customers/11"));

    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/api/customers");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({
      name: "Nueva",
      email: "nueva@example.test",
      phone: null,
      tax_id: null,
      address: null,
    });
  });

  it("patches the edit with all five fields and the captured version", async () => {
    fetchMock.mockResolvedValue(jsonResponse(customer, 200));
    renderForm({ mode: "edit", customer, resetSignal: 0, onReload: vi.fn() });
    const user = userEvent.setup();

    await user.type(screen.getByTestId("customers-form-name-input"), "!");
    await user.click(screen.getByTestId("customers-form-submit-button"));

    await waitFor(() => expect(routerMock.replace).toHaveBeenCalledWith("/customers/7"));

    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/api/customers/7");
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body as string)).toEqual({
      name: "Hotel Horizonte!",
      email: "hotel@example.test",
      phone: null,
      tax_id: "HOTE-800123",
      address: "Paseo del Prado 15",
      version: 3,
    });
  });

  it("ignores a second submit while one is pending", async () => {
    let respond!: (response: Response) => void;
    fetchMock.mockReturnValueOnce(
      new Promise<Response>((resolve) => {
        respond = resolve;
      }),
    );
    renderForm({ mode: "edit", customer, resetSignal: 0, onReload: vi.fn() });
    const user = userEvent.setup();

    await user.click(screen.getByTestId("customers-form-submit-button"));
    const submitButton = screen.getByTestId("customers-form-submit-button");
    expect(submitButton).toHaveTextContent("Guardando…");
    expect(submitButton).toHaveAttribute("data-state", "loading");
    expect(submitButton).toBeDisabled();

    // Even a request dispatched straight to the form, bypassing the
    // disabled button, is ignored by the handler guard.
    const form = document.querySelector(
      "[data-testid='customers-customer-form']",
    ) as HTMLFormElement;
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    respond(jsonResponse(customer, 200));
    await waitFor(() => expect(routerMock.replace).toHaveBeenCalledWith("/customers/7"));
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("the customer form client checks", () => {
  it("shows the required error on empty name and email without sending", async () => {
    renderForm({ mode: "create" });
    const user = userEvent.setup();

    await user.click(screen.getByTestId("customers-form-submit-button"));

    expect(screen.getByTestId("customers-form-name-error"))
      .toHaveTextContent("Este campo es obligatorio.");
    expect(screen.getByTestId("customers-form-email-error"))
      .toHaveTextContent("Este campo es obligatorio.");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("treats a whitespace-only name as empty but checks it trimmed", async () => {
    fetchMock.mockResolvedValue(jsonResponse(customer, 200));
    renderForm({ mode: "create" });
    const user = userEvent.setup();

    await user.type(screen.getByTestId("customers-form-name-input"), "  N ");
    await user.type(screen.getByTestId("customers-form-email-input"), "  a@b.test  ");
    await user.click(screen.getByTestId("customers-form-submit-button"));

    await waitFor(() => expect(routerMock.replace).toHaveBeenCalled());
    expect(
      screen.queryByTestId("customers-form-name-error"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("customers-form-email-error"),
    ).not.toBeInTheDocument();
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toMatchObject({
      name: "N",
      email: "a@b.test",
    });
  });

  it("focuses the first field with an error", async () => {
    renderForm({ mode: "create" });
    const user = userEvent.setup();

    await user.click(screen.getByTestId("customers-form-submit-button"));

    expect(document.activeElement).toHaveAttribute(
      "data-testid",
      "customers-form-name-input",
    );
  });
});

describe("the customer form server errors", () => {
  it("maps a 422 to the matching fields and focuses the first one", async () => {
    fetchMock.mockResolvedValue(problem({
      ...VALIDATION_PROBLEM,
      errors: [
        { field: "name", code: "TOO_SHORT", message: "Debe tener al menos 2 caracteres." },
        {
          field: "tax_id",
          code: "INVALID_FORMAT",
          message: "El formato no es válido.",
        },
      ],
    }));
    renderForm({ mode: "create" });
    const user = userEvent.setup();

    await user.type(screen.getByTestId("customers-form-name-input"), "A");
    await user.type(screen.getByTestId("customers-form-email-input"), "a@b.test");
    await user.click(screen.getByTestId("customers-form-submit-button"));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(screen.getByTestId("customers-form-name-error"))
      .toHaveTextContent("Debe tener al menos 2 caracteres.");
    // `tax_id` shows on the ID fiscal field.
    expect(screen.getByTestId("customers-form-taxid-error"))
      .toHaveTextContent("El formato no es válido.");
    expect(screen.queryByTestId("customers-form-alert")).not.toBeInTheDocument();
    expect(document.activeElement).toHaveAttribute(
      "data-testid",
      "customers-form-name-input",
    );
  });

  it("maps a 409 CUSTOMER_EMAIL_TAKEN to the email field", async () => {
    fetchMock.mockResolvedValue(problem({
      status: 409,
      code: "CUSTOMER_EMAIL_TAKEN",
      detail: "Ya existe un cliente con ese email.",
    }));
    renderForm({ mode: "create" });
    const user = userEvent.setup();

    await user.type(screen.getByTestId("customers-form-name-input"), "Otro");
    await user.type(screen.getByTestId("customers-form-email-input"),
      "hotel@example.test");
    await user.click(screen.getByTestId("customers-form-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("customers-form-email-error"))
        .toHaveTextContent("Ya existe un cliente con ese email.");
    });
    expect(document.activeElement).toHaveAttribute(
      "data-testid",
      "customers-form-email-input",
    );
  });

  it("maps a network failure to the form-level alert and focuses it", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    renderForm({ mode: "create" });
    const user = userEvent.setup();

    await user.type(screen.getByTestId("customers-form-name-input"), "Nueva");
    await user.type(screen.getByTestId("customers-form-email-input"),
      "nueva@example.test");
    await user.click(screen.getByTestId("customers-form-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("customers-form-alert"))
        .toHaveTextContent("Ocurrió un error inesperado. Inténtalo de nuevo.");
    });
    expect(document.activeElement).toHaveAttribute(
      "data-testid",
      "customers-form-alert",
    );
  });

  it("clears the errors of the previous submit", async () => {
    fetchMock.mockResolvedValueOnce(problem({
      ...VALIDATION_PROBLEM,
      errors: [
        { field: "email", code: "INVALID_FORMAT", message: "El formato no es válido." },
      ],
    }));
    fetchMock.mockResolvedValueOnce(jsonResponse(customer, 200));
    renderForm({ mode: "create" });
    const user = userEvent.setup();

    await user.type(screen.getByTestId("customers-form-name-input"), "Nueva");
    await user.type(screen.getByTestId("customers-form-email-input"), "bad");
    await user.click(screen.getByTestId("customers-form-submit-button"));
    await waitFor(() => {
      expect(screen.getByTestId("customers-form-email-error"))
        .toHaveTextContent("El formato no es válido.");
    });

    await user.clear(screen.getByTestId("customers-form-email-input"));
    await user.type(screen.getByTestId("customers-form-email-input"),
      "nueva@example.test");
    await user.click(screen.getByTestId("customers-form-submit-button"));

    await waitFor(() => expect(routerMock.replace).toHaveBeenCalled());
    expect(
      screen.queryByTestId("customers-form-email-error"),
    ).not.toBeInTheDocument();
  });
});

describe("the version conflict of the customer form", () => {
  const conflict = {
    status: 409,
    code: "VERSION_CONFLICT",
    detail: "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo.",
  };

  it("shows the conflict detail with a reload button", async () => {
    fetchMock.mockResolvedValue(problem(conflict));
    const onReload = vi.fn();
    renderForm({ mode: "edit", customer, resetSignal: 0, onReload });
    const user = userEvent.setup();

    await user.click(screen.getByTestId("customers-form-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("customers-form-alert"))
        .toHaveTextContent(conflict.detail);
    });
    expect(screen.getByTestId("customers-form-reload-button"))
      .toHaveTextContent("Recargar datos");
  });

  it("resets to the server values and version after reload", async () => {
    fetchMock.mockResolvedValue(problem(conflict));
    const onReload = vi.fn();
    const { rerender } = render(
      <QueryClientProvider client={queryClient}>
        <CustomerForm mode="edit" customer={customer} resetSignal={0} onReload={onReload} />
      </QueryClientProvider>,
    );
    const user = userEvent.setup();

    await user.type(screen.getByTestId("customers-form-name-input"), " extraño");
    await user.click(screen.getByTestId("customers-form-submit-button"));
    await waitFor(() => {
      expect(screen.getByTestId("customers-form-alert")).toBeInTheDocument();
    });

    // The page refetches and bumps the reset signal; the newer server
    // customer replaces the values and the captured version.
    const reloaded: Customer = { ...customer, name: "Servidor", version: 4 };
    rerender(
      <QueryClientProvider client={queryClient}>
        <CustomerForm mode="edit" customer={reloaded} resetSignal={1} onReload={onReload} />
      </QueryClientProvider>,
    );

    expect(screen.getByTestId("customers-form-name-input"))
      .toHaveValue("Servidor");
    expect(screen.getByTestId("customers-form-email-input"))
      .toHaveValue("hotel@example.test");

    // The next submit sends the reloaded version.
    fetchMock.mockResolvedValue(jsonResponse(reloaded, 200));
    await user.click(screen.getByTestId("customers-form-submit-button"));
    await waitFor(() => expect(routerMock.replace).toHaveBeenCalledWith("/customers/7"));
    const [, init] = fetchMock.mock.calls[1] as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toMatchObject({ version: 4 });
  });

  it("does not send the version of a later background refetch", async () => {
    const view = render(
      <QueryClientProvider client={queryClient}>
        <CustomerForm mode="edit" customer={customer} resetSignal={0} onReload={vi.fn()} />
      </QueryClientProvider>,
    );

    // The user edits while the form is open.
    const user = userEvent.setup();
    await user.type(screen.getByTestId("customers-form-name-input"), "!");

    // A background refetch brings a newer version while the form stays
    // open: the page rerenders with the fresh customer, but the values and
    // the captured version stay exactly as they were.
    const refetched: Customer = { ...customer, version: 9 };
    view.rerender(
      <QueryClientProvider client={queryClient}>
        <CustomerForm mode="edit" customer={refetched} resetSignal={0} onReload={vi.fn()} />
      </QueryClientProvider>,
    );

    fetchMock.mockResolvedValue(jsonResponse(refetched, 200));
    await user.click(screen.getByTestId("customers-form-submit-button"));
    await waitFor(() => expect(routerMock.replace).toHaveBeenCalledWith("/customers/7"));

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    // The stale version (captured at init), never the refetched one.
    expect(JSON.parse(init.body as string)).toMatchObject({ version: 3 });
  });
});
