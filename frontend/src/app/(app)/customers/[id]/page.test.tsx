import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CustomerDetailPage from "./page";
import type { Customer } from "@/features/customers/types";

const state = vi.hoisted(() => ({
  params: { id: "4" },
  router: {
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  },
}));

vi.mock("next/navigation", () => ({
  useParams: () => state.params,
  useRouter: () => state.router,
}));

const fetchMock = vi.fn();

let queryClient: QueryClient;
/** Who the mocked /api/auth/me answers. */
let meUser: Record<string, unknown>;

/** Answers to /api/customers/{id}* requests, consumed in order. */
const customerQueue: Array<() => Response> = [];

const activeCustomer: Customer = {
  id: 4,
  name: "Distribuidora Delta",
  email: "delta@example.test",
  phone: "+1 555 010 0004",
  tax_id: "DELT-700789",
  address: "Calle Mayor 45",
  status: "active",
  version: 2,
  created_at: "2026-01-01T09:04:00Z",
  updated_at: "2026-01-01T09:04:00Z",
};

const inactiveCustomer: Customer = {
  ...activeCustomer,
  id: 8,
  phone: null,
  tax_id: null,
  address: null,
  status: "inactive",
  version: 1,
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

function problemResponse(
  status: number,
  code: string,
  detail: string,
): Response {
  return jsonResponse({ status, code, detail }, status);
}

/** The /api/customers requests with method, url and headers. */
function customersCalls(): Array<{ url: string; init: RequestInit }> {
  return fetchMock.mock.calls
    .map((call) => ({ url: String(call[0]), init: call[1] as RequestInit }))
    .filter((call) => call.url.startsWith("/api/customers"));
}

function renderAt(id: string) {
  state.params = { id };
  return render(
    <QueryClientProvider client={queryClient}>
      <CustomerDetailPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  customerQueue.length = 0;
  meUser = { id: 1, name: "Admin Demo", email: "admin@labapp.test", role: "admin" };
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
    if (/^\/api\/customers/.test(url)) {
      return (customerQueue.shift() ??
        (() => problemResponse(404, "NOT_FOUND", "No se encontró el recurso solicitado.")))();
    }
    return problemResponse(404, "NOT_FOUND", "No se encontró el recurso solicitado.");
  });
});

afterEach(() => {
  document.title = "LabApp";
  vi.unstubAllGlobals();
});

describe("the customer detail values", () => {
  it("names the customer in the tab once the record arrives", async () => {
    customerQueue.push(() => jsonResponse(activeCustomer));
    renderAt("4");

    // The section title is the first thing the tab answers, both for a
    // loading request...
    expect(document.title).toBe("Clientes · LabApp");

    // ...and the customer's name replaces it when the answer is in.
    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-heading"))
        .toHaveTextContent("Distribuidora Delta");
    });
    expect(document.title).toBe("Cliente Distribuidora Delta · LabApp");
  });

  it("shows the heading and every labeled value", async () => {
    customerQueue.push(() => jsonResponse(activeCustomer));
    renderAt("4");

    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-heading"))
        .toHaveTextContent("Distribuidora Delta");
    });

    expect(screen.getByTestId("customers-detail-name-text"))
      .toHaveTextContent("Distribuidora Delta");
    expect(screen.getByTestId("customers-detail-email-text"))
      .toHaveTextContent("delta@example.test");
    expect(screen.getByTestId("customers-detail-phone-text"))
      .toHaveTextContent("+1 555 010 0004");
    expect(screen.getByTestId("customers-detail-taxid-text"))
      .toHaveTextContent("DELT-700789");
    expect(screen.getByTestId("customers-detail-address-text"))
      .toHaveTextContent("Calle Mayor 45");
    expect(screen.getByTestId("customers-detail-state-status"))
      .toHaveTextContent("Activo");

    expect(screen.getByTestId("customers-detail-back-link")).toHaveAttribute(
      "href",
      "/customers",
    );
    expect(screen.getByTestId("customers-detail-edit-link")).toHaveAttribute(
      "href",
      "/customers/4/edit",
    );
  });

  it("shows — for every null field and Inactivo for an inactive customer", async () => {
    customerQueue.push(() => jsonResponse(inactiveCustomer));
    renderAt("8");

    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-state-status"))
        .toHaveTextContent("Inactivo");
    });
    expect(screen.getByTestId("customers-detail-phone-text"))
      .toHaveTextContent("—");
    expect(screen.getByTestId("customers-detail-taxid-text"))
      .toHaveTextContent("—");
    expect(screen.getByTestId("customers-detail-address-text"))
      .toHaveTextContent("—");
  });
});

describe("the customer detail actions", () => {
  it("offers Deactivar for an active customer", async () => {
    customerQueue.push(() => jsonResponse(activeCustomer));
    renderAt("4");

    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-deactivate-button"))
        .toHaveTextContent("Desactivar");
    });
    expect(
      screen.queryByTestId("customers-detail-reactivate-button"),
    ).not.toBeInTheDocument();
  });

  it("offers Reactivar for an inactive customer", async () => {
    customerQueue.push(() => jsonResponse(inactiveCustomer));
    renderAt("8");

    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-reactivate-button"))
        .toHaveTextContent("Reactivar");
    });
    expect(
      screen.queryByTestId("customers-detail-deactivate-button"),
    ).not.toBeInTheDocument();
  });

  it("hides the write controls for a role that cannot manage customers", async () => {
    meUser = { id: 4, name: "Solo Lectura Demo", email: "readonly@labapp.test", role: "readonly" };
    customerQueue.push(() => jsonResponse(activeCustomer));
    renderAt("4");

    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-taxid-text"))
        .toHaveTextContent("DELT-700789");
    });
    expect(screen.queryByTestId("customers-detail-edit-link")).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("customers-detail-deactivate-button"),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("customers-detail-back-link")).toBeInTheDocument();
  });

  it("changes the screen without reloading when the status change succeeds", async () => {
    const updated: Customer = { ...activeCustomer, status: "inactive", version: 3 };
    customerQueue.push(() => jsonResponse(activeCustomer));
    customerQueue.push(() => jsonResponse(updated));
    renderAt("4");

    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-deactivate-button")).toBeInTheDocument();
    });

    await userEvent.setup().click(screen.getByTestId("customers-detail-deactivate-button"));

    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-reactivate-button"))
        .toHaveTextContent("Reactivar");
    });
    expect(screen.getByTestId("customers-detail-state-status"))
      .toHaveTextContent("Inactivo");

    // POST /api/customers/4/deactivate with the on-screen version.
    expect(customersCalls()).toEqual([
      { url: "/api/customers/4", init: expect.objectContaining({ method: "GET" }) },
      {
        url: "/api/customers/4/deactivate",
        init: expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({ "If-Match": '"2"' }),
        }),
      },
    ]);
    // No reloading: the shell router was never called.
    expect(state.router.replace).not.toHaveBeenCalled();
    expect(state.router.push).not.toHaveBeenCalled();
  });

  it("ignores a second click while the status change runs", async () => {
    let respond!: (response: Response) => void;
    const pending = new Promise<Response>((resolve) => {
      respond = resolve;
    });
    customerQueue.push(() => jsonResponse(activeCustomer));
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/auth/me") {
        return jsonResponse(meUser);
      }
      if (url === "/api/customers/4") {
        return jsonResponse(activeCustomer);
      }
      if (url === "/api/customers/4/deactivate") {
        return pending;
      }
      return problemResponse(404, "NOT_FOUND", "no");
    });
    renderAt("4");

    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-deactivate-button")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByTestId("customers-detail-deactivate-button"));
    const button = screen.getByTestId("customers-detail-deactivate-button");
    expect(button).toHaveAttribute("data-state", "loading");
    expect(button).toBeDisabled();

    // A dispatch straight to the detached control is also ignored.
    button.dispatchEvent(new Event("click", { bubbles: true }));
    respond(jsonResponse({ ...activeCustomer, status: "inactive", version: 3 }));
    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-reactivate-button")).toBeInTheDocument();
    });
  });

  it("shows the failure detail and refetches so the next click uses the fresh version", async () => {
    const fresh: Customer = { ...activeCustomer, status: "inactive", version: 3 };
    customerQueue.push(() => jsonResponse(activeCustomer)); // initial load: version 2
    customerQueue.push(() =>
      problemResponse(
        409,
        "VERSION_CONFLICT",
        "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo.",
      ),
    );
    customerQueue.push(() => jsonResponse(fresh)); // the refetch after the failure
    customerQueue.push(() => jsonResponse(fresh)); // the successful second attempt
    renderAt("4");

    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-deactivate-button")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByTestId("customers-detail-deactivate-button"));

    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-alert")).toHaveTextContent(
        "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo.",
      );
    });
    expect(screen.getByTestId("customers-detail-state-status"))
      // The refetch made the screen show the server state.
      .toHaveTextContent("Inactivo");

    // The alert did not block a new attempt: the fresh version is sent.
    await user.click(screen.getByTestId("customers-detail-reactivate-button"));
    await waitFor(() => {
      expect(state.router.replace).not.toHaveBeenCalled();
      expect(customersCalls().length).toBe(4);
    });

    const calls = customersCalls();
    expect(calls.map((call) => call.url)).toEqual([
      "/api/customers/4",
      "/api/customers/4/deactivate",
      "/api/customers/4",
      "/api/customers/4/reactivate",
    ]);
    expect(
      (calls[3].init.headers as Record<string, string>)["If-Match"],
    ).toBe('"3"');
  });

  it("refetches after any failed status change", async () => {
    customerQueue.push(() => jsonResponse(activeCustomer)); // initial load
    customerQueue.push(() =>
      problemResponse(500, "INTERNAL_ERROR", "Ocurrió un error inesperado. Inténtalo de nuevo."),
    );
    customerQueue.push(() => jsonResponse(activeCustomer)); // refetch after the failure
    renderAt("4");

    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-deactivate-button")).toBeInTheDocument();
    });

    await userEvent.setup().click(screen.getByTestId("customers-detail-deactivate-button"));

    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-alert")).toHaveTextContent(
        "Ocurrió un error inesperado. Inténtalo de nuevo.",
      );
    });
    await waitFor(() => {
      expect(customersCalls().map((call) => ({ url: call.url, method: call.init.method })))
        .toEqual([
          { url: "/api/customers/4", method: "GET" },
          { url: "/api/customers/4/deactivate", method: "POST" },
          { url: "/api/customers/4", method: "GET" },
        ]);
    });
  });
});

describe("the customer detail load states", () => {
  it("shows the loading status while the customer loads", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      if (String(input) === "/api/auth/me") {
        return jsonResponse(meUser);
      }
      return new Promise<Response>(() => {});
    });

    renderAt("4");

    const status = screen.getByTestId("customers-detail-loading-status");
    expect(status).toHaveTextContent("Cargando…");
    expect(status).toHaveAttribute("aria-busy", "true");
  });

  it("shows the problem detail with a retry for a load failure", async () => {
    customerQueue.push(() =>
      problemResponse(500, "INTERNAL_ERROR", "Ocurrió un error inesperado. Inténtalo de nuevo."),
    );
    customerQueue.push(() => jsonResponse(activeCustomer));
    renderAt("4");

    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-error-alert")).toHaveTextContent(
        "Ocurrió un error inesperado. Inténtalo de nuevo.",
      );
    });

    await userEvent.setup().click(screen.getByTestId("customers-detail-retry-button"));
    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-heading"))
        .toHaveTextContent("Distribuidora Delta");
    });
  });

  it("shows the 404 detail with only the back link", async () => {
    customerQueue.push(() =>
      problemResponse(404, "NOT_FOUND", "No se encontró el recurso solicitado."),
    );
    renderAt("999");

    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-error-alert")).toHaveTextContent(
        "No se encontró el recurso solicitado.",
      );
    });
    expect(screen.getByTestId("customers-detail-back-link")).toBeInTheDocument();
    expect(
      screen.queryByTestId("customers-detail-retry-button"),
    ).not.toBeInTheDocument();
  });

  it("rejects an invalid id without calling the API", async () => {
    customerQueue.push(() => jsonResponse(activeCustomer));
    renderAt("007");

    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-error-alert")).toHaveTextContent(
        "No se encontró el recurso solicitado.",
      );
    });
    expect(screen.getByTestId("customers-detail-back-link")).toBeInTheDocument();
    expect(customersCalls()).toEqual([]);
    expect(customerQueue).toHaveLength(1);
  });

  it("rejects the 1e3 id the same way", async () => {
    renderAt("1e3");

    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-error-alert")).toBeInTheDocument();
    });
    expect(customersCalls()).toEqual([]);
  });
});

describe("the orders section of the customer detail", () => {
  it("links the orders of an active customer", async () => {
    customerQueue.push(() => jsonResponse(activeCustomer));
    renderAt("4");

    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-orders-link"))
        .toHaveAttribute("href", "/orders?customer_id=4");
    });
    expect(
      screen.getByTestId("customers-detail-orders-link"),
    ).toHaveTextContent("Ver pedidos de este cliente");
    expect(screen.getByTestId("customers-detail-orders-heading"))
      .toHaveTextContent("Pedidos");
    expect(
      screen.getByTestId("customers-detail-orders-heading").tagName,
    ).toBe("H2");
  });

  it("links the orders of an inactive customer too", async () => {
    customerQueue.push(() => jsonResponse(inactiveCustomer));
    renderAt("8");

    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-orders-link"))
        .toHaveAttribute("href", "/orders?customer_id=8");
    });
    expect(screen.getByTestId("customers-detail-orders-link"))
      .toHaveTextContent("Ver pedidos de este cliente");
  });

  it("keeps the section visible for a role that cannot manage customers", async () => {
    meUser = {
      id: 4,
      name: "Solo Lectura Demo",
      email: "readonly@labapp.test",
      role: "readonly",
    };
    customerQueue.push(() => jsonResponse(activeCustomer));
    renderAt("4");

    await waitFor(() => {
      expect(screen.getByTestId("customers-detail-orders-link"))
        .toBeInTheDocument();
    });
    expect(
      screen.queryByTestId("customers-detail-edit-link"),
    ).not.toBeInTheDocument();
  });
});
