import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CustomerCreatePage from "./page";
import type { Customer } from "@/features/customers/types";

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
  useSearchParams: () => new URLSearchParams(),
}));

const fetchMock = vi.fn();

let queryClient: QueryClient;

let meUser: Record<string, unknown>;

/** The body and status of the mocked /api/customers list. */
let customersBody: unknown;
let customersStatus: number;

/** The body, status and headers of the mocked POST /api/orders. */
let createBody: unknown;
let createStatus: number;

const adminUser = {
  id: 1,
  name: "Admin Demo",
  email: "admin@labapp.test",
  role: "admin",
};

const readonlyUser = {
  id: 4,
  name: "Solo Lectura Demo",
  email: "readonly@labapp.test",
  role: "readonly",
};

function customer(id: number, overrides: Partial<Customer> = {}): Customer {
  return {
    id,
    name: `Cliente ${id}`,
    email: `cliente${id}@example.test`,
    phone: null,
    tax_id: null,
    address: null,
    status: "active",
    version: 1,
    created_at: "2026-01-01T09:00:00Z",
    updated_at: "2026-01-01T09:00:00Z",
    ...overrides,
  };
}

const draftOrder = {
  id: 8,
  number: "PED-0008",
  status: "draft",
  customer: { id: 1, name: "Acme Industrial S.A.", status: "active" },
  lines: [],
  subtotal: "0.00",
  tax_rate: "10.00",
  tax: "0.00",
  total: "0.00",
  invoice_id: null,
  version: 1,
  created_at: "2026-11-05T15:00:00Z",
  updated_at: "2026-11-05T15:00:00Z",
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

function problem(status: number, code: string, detail: string, errors?: unknown) {
  return jsonResponse(
    errors === undefined
      ? { status, code, detail }
      : { status, code, detail, errors },
    status,
  );
}

function renderPage() {
  render(
    <QueryClientProvider client={queryClient}>
      <CustomerCreatePage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  routerMock.replace.mockClear();
  meUser = adminUser;
  customersBody = {
    items: [customer(1, { name: "Acme Industrial S.A." }), customer(6, { name: "Ferretería Fénix" })],
    page: 1,
    page_size: 20,
    total: 2,
  };
  customersStatus = 200;
  createBody = null;
  createStatus = 201;
  queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/auth/me") {
      return jsonResponse(meUser);
    }
    if (url.startsWith("/api/customers")) {
      return jsonResponse(customersBody, customersStatus);
    }
    if (url === "/api/orders") {
      return createBody === null
        ? problem(500, "INTERNAL_ERROR", "Ocurrió un error inesperado. Inténtalo de nuevo.")
        : jsonResponse(createBody, createStatus);
    }
    return problem(404, "NOT_FOUND", "No se encontró el recurso solicitado.");
  });
});

afterEach(() => {
  document.title = "LabApp";
  vi.unstubAllGlobals();
});

describe("the create page structure", () => {
  it("titles the document Nuevo pedido before anything loads", async () => {
    renderPage();

    expect(document.title).toBe("Nuevo pedido · LabApp");
    await waitFor(() => {
      expect(screen.getByTestId("orders-customer-form")).toBeInTheDocument();
    });
  });

  it("renders the heading, the two forms and the picker", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("orders-customer-form")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: "Nuevo pedido" }))
      .toHaveAttribute("data-testid", "orders-form-heading");

    // The search is its own form, never nested inside the one that
    // submits (B3).
    const searchForm = screen.getByTestId("orders-form-customersearch-form");
    const submitForm = screen.getByTestId("orders-customer-form");
    expect(searchForm.contains(submitForm)).toBe(false);
    expect(
      screen.getByTestId("orders-form-customersearch-input"),
    ).toHaveAccessibleName("Buscar cliente");
    expect(
      screen.getByTestId("orders-form-customersearch-button"),
    ).toHaveTextContent("Buscar");

    const select = screen.getByTestId(
      "orders-form-customer-select",
    ) as HTMLSelectElement;
    // B3: the select starts with a disabled placeholder option.
    expect(select.value).toBe("");
    const placeholder = select.options[0];
    expect(placeholder.textContent).toBe("Elige un cliente");
    expect(placeholder.disabled).toBe(true);
    expect(
      Array.from(select.options).map((option) => option.textContent),
    ).toContain("Acme Industrial S.A.");

    expect(screen.getByTestId("orders-form-customer-text")).toHaveTextContent(
      "Se muestran hasta 20 clientes activos; usa la búsqueda para encontrar otro.",
    );
    expect(screen.getByTestId("orders-form-cancel-link")).toHaveAttribute(
      "href",
      "/orders",
    );
  });

  it("disables the submit until a customer is chosen", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("orders-customer-form")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    expect(screen.getByTestId("orders-form-submit-button")).toBeDisabled();

    await user.selectOptions(
      screen.getByTestId("orders-form-customer-select"),
      "1",
    );
    expect(screen.getByTestId("orders-form-submit-button")).toBeEnabled();
  });

  it("shows the picker states: loading, empty and load error with retry", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/auth/me") {
        return jsonResponse(meUser);
      }
      if (url.startsWith("/api/customers")) {
        return new Promise<Response>(() => {});
      }
      if (url === "/api/orders") {
        return jsonResponse(draftOrder, 201);
      }
      return problem(404, "NOT_FOUND", "No se encontró el recurso solicitado.");
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("orders-form-customer-loading-status"))
        .toHaveTextContent("Buscando clientes…");
    });
    expect(screen.getByTestId("orders-form-customer-loading-status"))
      .toHaveAttribute("aria-busy", "true");

    // While loading, the select holds only the placeholder; the submit
    // stays disabled until a customer is chosen.
    const select = screen.getByTestId(
      "orders-form-customer-select",
    ) as HTMLSelectElement;
    expect(select.options.length).toBe(1);
    expect(select.options[0].textContent).toBe("Elige un cliente");
    expect(screen.getByTestId("orders-form-submit-button")).toBeDisabled();
  });

  it("shows the empty state when no active customer matches", async () => {
    customersBody = { items: [], page: 1, page_size: 20, total: 0 };
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("orders-form-customer-empty-status"))
        .toHaveTextContent("No hay clientes activos que coincidan.");
    });
    expect(screen.getByTestId("orders-customer-form")).toBeInTheDocument();
    expect(screen.getByTestId("orders-form-submit-button")).toBeDisabled();
  });

  it("shows the customers load failure in the form error alert with retry", async () => {
    customersStatus = 500;
    customersBody = {
      status: 500,
      code: "INTERNAL_ERROR",
      detail: "Ocurrió un error inesperado. Inténtalo de nuevo.",
    };
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("orders-form-error-alert")).toHaveTextContent(
        "Ocurrió un error inesperado. Inténtalo de nuevo.",
      );
    });
    expect(screen.getByTestId("orders-form-retry-button")).toBeEnabled();

    // The retry recovers and shows the picker options.
    customersStatus = 200;
    customersBody = { items: [customer(1)], page: 1, page_size: 20, total: 1 };
    await userEvent.setup().click(screen.getByTestId("orders-form-retry-button"));
    await waitFor(() => {
      expect(screen.getByTestId("orders-customer-form")).toBeInTheDocument();
    });
    expect(
      screen.queryByTestId("orders-form-error-alert"),
    ).not.toBeInTheDocument();
  });

  it("shows only the permission alert for roles that cannot edit orders", async () => {
    meUser = readonlyUser;
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("orders-form-forbidden-alert"))
        .toHaveTextContent("No tienes permiso para realizar esta acción.");
    });
    await waitFor(() => {
      expect(screen.queryByTestId("orders-customer-form")).not.toBeInTheDocument();
    });
    expect(
      screen.queryByTestId("orders-form-customersearch-form"),
    ).not.toBeInTheDocument();
  });
});

describe("the create page picker search", () => {
  it("applies the search only on submit, with q encoded", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("orders-customer-form")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.type(
      screen.getByTestId("orders-form-customersearch-input"),
      " Ám &ca ",
    );
    await user.click(screen.getByTestId("orders-form-customersearch-button"));

    const listCalls = fetchMock.mock.calls
      .map((call) => String(call[0]))
      .filter((url) => url.startsWith("/api/customers"));
    expect(listCalls.length).toBeGreaterThan(1);
    // Nothing was applied while typing: only the submit changes the query.
    expect(listCalls[0]).toBe("/api/customers?page=1&status=active");
    // URLSearchParams encodes the space as `+` and the ampersand as %26.
    expect(listCalls.at(-1)).toBe(
      "/api/customers?page=1&q=%C3%81m+%26ca&status=active",
    );
  });

  it("resets the choice when a new search drops the chosen customer", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("orders-customer-form")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.selectOptions(screen.getByTestId("orders-form-customer-select"), "1");
    expect(screen.getByTestId("orders-form-submit-button")).toBeEnabled();

    // A search that returns someone else empties the choice.
    await user.type(screen.getByTestId("orders-form-customersearch-input"), "fénix");
    customersBody = {
      items: [customer(6, { name: "Ferretería Fénix" })],
      page: 1,
      page_size: 20,
      total: 1,
    };
    await user.click(screen.getByTestId("orders-form-customersearch-button"));
    await waitFor(() => {
      const select = screen.getByTestId(
        "orders-form-customer-select",
      ) as HTMLSelectElement;
      expect(select.value).toBe("");
    });
    expect(screen.getByTestId("orders-form-submit-button")).toBeDisabled();

    // The placeholder is selected again; no option is missing from the
    // list the state could point at.
    customersBody = {
      items: [customer(6, { name: "Ferretería Fénix" })],
      page: 1,
      page_size: 20,
      total: 1,
    };
  });
});

describe("the create page submit", () => {
  async function chooseCustomer() {
    const user = userEvent.setup();
    await waitFor(
      () => expect(screen.getByTestId("orders-customer-form")).toBeInTheDocument(),
    );
    await user.selectOptions(
      screen.getByTestId("orders-form-customer-select"),
      "1",
    );
    return user;
  }

  it("posts the customer id and redirects to the detail of the new order", async () => {
    createBody = draftOrder;
    createStatus = 201;
    renderPage();
    const user = await chooseCustomer();

    await user.click(screen.getByTestId("orders-form-submit-button"));

    await waitFor(() => {
      expect(routerMock.replace).toHaveBeenCalledWith("/orders/8");
    });
    expect(fetchMock.mock.calls.find((call) => String(call[0]) === "/api/orders"))
      .toEqual([
        "/api/orders",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ customer_id: 1 }),
        }),
      ]);
  });

  it("shows a 422 on customer_id on the select", async () => {
    createStatus = 422;
    createBody = {
      type: "about:blank",
      title: "Unprocessable Content",
      status: 422,
      code: "VALIDATION_ERROR",
      detail: "Revisa los datos ingresados.",
      errors: [
        {
          field: "customer_id",
          code: "REFERENCE_NOT_FOUND",
          message: "El registro indicado no existe.",
        },
      ],
    };
    renderPage();
    const user = await chooseCustomer();

    await user.click(screen.getByTestId("orders-form-submit-button"));

    const alert = await waitFor(() => {
      const element = screen.getByTestId("orders-form-customer-error");
      expect(element).toHaveTextContent("El registro indicado no existe.");
      return element;
    });
    expect(alert).toHaveAttribute("role", "alert");
    // The field is the focus target...
    expect(document.activeElement).toHaveAttribute(
      "data-testid",
      "orders-form-customer-select",
    );
    // ...and no form-level alert is shown.
    expect(screen.queryByTestId("orders-form-alert")).not.toBeInTheDocument();
  });

  it("shows CUSTOMER_INACTIVE on the select and CUSTOMER_INACTIVE's detail", async () => {
    createStatus = 422;
    createBody = {
      status: 422,
      code: "CUSTOMER_INACTIVE",
      detail: "El cliente no está activo.",
    };
    renderPage();
    const user = await chooseCustomer();

    await user.click(screen.getByTestId("orders-form-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("orders-form-customer-error")).toHaveTextContent(
        "El cliente no está activo.",
      );
    });
    expect(document.activeElement).toHaveAttribute(
      "data-testid",
      "orders-form-customer-select",
    );
  });

  it("shows any other problem in the form alert and focuses it", async () => {
    createStatus = 403;
    createBody = {
      status: 403,
      code: "FORBIDDEN",
      detail: "No tienes permiso para realizar esta acción.",
    };
    renderPage();
    const user = await chooseCustomer();

    await user.click(screen.getByTestId("orders-form-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("orders-form-alert")).toHaveTextContent(
        "No tienes permiso para realizar esta acción.",
      );
    });
    expect(screen.getByTestId("orders-form-alert")).toHaveAttribute("tabindex", "-1");
    expect(document.activeElement).toHaveAttribute(
      "data-testid",
      "orders-form-alert",
    );
  });

  it("shows the INTERNAL_ERROR text for a network failure", async () => {
    renderPage();
    const user = await chooseCustomer();
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      if (String(input) === "/api/auth/me") {
        return jsonResponse(meUser);
      }
      if (String(input).startsWith("/api/customers")) {
        return jsonResponse(customersBody, customersStatus);
      }
      throw new TypeError("Failed to fetch");
    });

    await user.click(screen.getByTestId("orders-form-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("orders-form-alert")).toHaveTextContent(
        "Ocurrió un error inesperado. Inténtalo de nuevo.",
      );
    });
    expect(routerMock.replace).not.toHaveBeenCalled();
  });

  it("ignores a second submit while one is pending", async () => {
    let release!: (response: Response) => void;
    const gate = new Promise<Response>((resolve) => {
      release = resolve;
    });
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/auth/me") {
        return jsonResponse(meUser);
      }
      if (url.startsWith("/api/customers")) {
        return jsonResponse(customersBody, customersStatus);
      }
      if (url === "/api/orders") {
        return gate;
      }
      return problem(404, "NOT_FOUND", "No se encontró el recurso solicitado.");
    });
    renderPage();
    const user = await chooseCustomer();

    await user.click(screen.getByTestId("orders-form-submit-button"));
    const submit = screen.getByTestId("orders-form-submit-button");
    expect(submit).toBeDisabled();
    expect(submit).toHaveAttribute("data-state", "loading");
    expect(submit).toHaveAttribute("aria-busy", "true");
    expect(submit).toHaveTextContent("Crear pedido");

    // Even a submit dispatched straight to the form, bypassing the
    // disabled button, is ignored by the handler guard.
    const form = document.querySelector(
      "[data-testid='orders-customer-form']",
    ) as HTMLFormElement;
    form.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    await waitFor(() => {
      expect(fetchMock.mock.calls.filter((call) => String(call[0]) === "/api/orders"))
        .toHaveLength(1);
    });

    release(jsonResponse(draftOrder, 201));
    await waitFor(() => {
      expect(routerMock.replace).toHaveBeenCalledWith("/orders/8");
    });
  });
});
