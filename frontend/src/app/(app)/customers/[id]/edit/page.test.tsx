import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { customerDetailKey } from "@/features/customers/hooks";
import type { Customer } from "@/features/customers/types";
import CustomerEditPage from "./page";

const state = vi.hoisted(() => ({
  params: { id: "7" },
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

/** Answers to /api/customers/7* requests, consumed in order. */
const customerQueue: Array<() => Response> = [];

/** A scorer of every /api/customers request. */
function customersCalls(): Array<{ url: string; init: RequestInit }> {
  return fetchMock.mock.calls
    .map((call) => ({ url: String(call[0]), init: call[1] as RequestInit }))
    .filter((call) => call.url.startsWith("/api/customers"));
}

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

function renderEdit(searchId = "7") {
  state.params = { id: searchId };
  return render(
    <QueryClientProvider client={queryClient}>
      <CustomerEditPage />
    </QueryClientProvider>,
  );
}

const CONFLICT_PROBLEM = {
  status: 409,
  code: "VERSION_CONFLICT",
  detail: "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo.",
};

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
  vi.unstubAllGlobals();
});

describe("the edit page load states", () => {
  it("renders the form prefilled with the server values", async () => {
    customerQueue.push(() => jsonResponse(customer));
    renderEdit();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Editar cliente" }))
        .toHaveAttribute("data-testid", "customers-form-heading");
    });

    expect(screen.getByTestId("customers-form-name-input"))
      .toHaveValue("Hotel Horizonte");
    expect(screen.getByTestId("customers-form-email-input"))
      .toHaveValue("hotel@example.test");
    expect(screen.getByTestId("customers-form-taxid-input"))
      .toHaveValue("HOTE-800123");
    expect(screen.getByTestId("customers-form-address-textarea"))
      .toHaveValue("Paseo del Prado 15");
    expect(screen.getByTestId("customers-form-cancel-link"))
      .toHaveAttribute("href", "/customers/7");
  });

  it("shows a busy status while the customer and the session load", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      if (String(input) === "/api/auth/me") {
        return jsonResponse(meUser);
      }
      return new Promise<Response>(() => {});
    });

    renderEdit();

    const status = screen.getByTestId("customers-form-loading-status");
    expect(status).toHaveTextContent("Cargando…");
    expect(status).toHaveAttribute("aria-busy", "true");
  });

  it("shows the problem detail with a retry for a load failure", async () => {
    customerQueue.push(() =>
      problemResponse(500, "INTERNAL_ERROR", "Ocurrió un error inesperado. Inténtalo de nuevo."),
    );
    customerQueue.push(() => jsonResponse(customer));
    renderEdit();

    await waitFor(() => {
      expect(screen.getByTestId("customers-form-error-alert")).toHaveTextContent(
        "Ocurrió un error inesperado. Inténtalo de nuevo.",
      );
    });
    await userEvent.setup().click(screen.getByTestId("customers-form-retry-button"));
    await waitFor(() => {
      expect(screen.getByTestId("customers-form-heading"))
        .toHaveTextContent("Editar cliente");
    });
  });

  it("shows the 404 detail without a retry button", async () => {
    customerQueue.push(() =>
      problemResponse(404, "NOT_FOUND", "No se encontró el recurso solicitado."),
    );
    renderEdit("999");

    await waitFor(() => {
      expect(screen.getByTestId("customers-form-error-alert")).toHaveTextContent(
        "No se encontró el recurso solicitado.",
      );
    });
    expect(
      screen.queryByTestId("customers-form-retry-button"),
    ).not.toBeInTheDocument();
  });

  it("rejects an invalid id without calling the API", async () => {
    customerQueue.push(() => jsonResponse(customer));
    renderEdit("007");

    await waitFor(() => {
      expect(screen.getByTestId("customers-form-error-alert")).toHaveTextContent(
        "No se encontró el recurso solicitado.",
      );
    });
    expect(screen.getByTestId("customers-form-cancel-link")).toBeInTheDocument();
    expect(customersCalls()).toEqual([]);
    expect(customerQueue).toHaveLength(1);
  });

  it("shows only the permission alert for a role that cannot manage customers", async () => {
    meUser = { id: 3, name: "Finanzas Demo", email: "finance@labapp.test", role: "finance" };
    customerQueue.push(() => jsonResponse(customer));
    renderEdit();

    await waitFor(() => {
      expect(screen.getByTestId("customers-form-forbidden-alert")).toHaveTextContent(
        "No tienes permiso para realizar esta acción.",
      );
    });
    expect(screen.queryByTestId("customers-form-heading")).not.toBeInTheDocument();
    expect(screen.queryByTestId("customers-form-name-input")).not.toBeInTheDocument();
  });
});

describe("the version captured by the edit page", () => {
  it("sends the captured version despite a background refetch to a newer one", async () => {
    customerQueue.push(() => jsonResponse(customer)); // initial load: version 3
    customerQueue.push(() =>
      jsonResponse({ ...customer, name: "Servidor Horizonte", version: 9 }),
    ); // the background refetch: version 9
    customerQueue.push(() => jsonResponse({ ...customer, version: 10 }));
    // …the successful save
    renderEdit();

    await waitFor(() => {
      expect(screen.getByTestId("customers-form-name-input")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.type(screen.getByTestId("customers-form-name-input"), "!");

    // A background refetch of the same detail query (as a window focus
    // refetch does) brings a newer version while the form stays open.
    await queryClient.refetchQueries({ queryKey: customerDetailKey(7) });
    await waitFor(() => {
      expect(customersCalls().length).toBe(2);
    });

    state.router.replace.mockClear();
    await user.click(screen.getByTestId("customers-form-submit-button"));
    await waitFor(() => {
      expect(state.router.replace).toHaveBeenCalledWith("/customers/7");
    });

    // The version captured at the form init wins, never the refetched one.
    const patchBody = JSON.parse(
      (customersCalls()[2].init as { body: string }).body,
    );
    expect(patchBody.version).toBe(3);
    // The user's edits are untouched by the refetch.
    expect(patchBody.name).toBe("Hotel Horizonte!");
  });

  it("recovers from a version conflict by reloading the server data", async () => {
    customerQueue.push(() => jsonResponse(customer)); // initial load: version 3
    customerQueue.push(() => jsonResponse(CONFLICT_PROBLEM, 409)); // the save fails
    customerQueue.push(() =>
      jsonResponse({ ...customer, name: "Servidor Horizonte", version: 9 }),
    );
    // the reload after the conflict
    customerQueue.push(() => jsonResponse({ ...customer, version: 10 }));
    // …the second save succeeds
    renderEdit();

    await waitFor(() => {
      expect(screen.getByTestId("customers-form-name-input")).toBeInTheDocument();
    });
    const user = userEvent.setup();

    await user.click(screen.getByTestId("customers-form-submit-button"));
    await waitFor(() => {
      expect(screen.getByTestId("customers-form-alert")).toHaveTextContent(
        CONFLICT_PROBLEM.detail,
      );
    });
    expect(screen.getByTestId("customers-form-reload-button"))
      .toHaveTextContent("Recargar datos");

    await user.click(screen.getByTestId("customers-form-reload-button"));
    await waitFor(() => {
      expect(screen.getByTestId("customers-form-name-input"))
        .toHaveValue("Servidor Horizonte");
    });
    // The reset also cleared the conflict alert.
    expect(screen.queryByTestId("customers-form-alert")).not.toBeInTheDocument();

    await user.click(screen.getByTestId("customers-form-submit-button"));
    await waitFor(() => {
      expect(state.router.replace).toHaveBeenCalledWith("/customers/7");
    });
    expect(customersCalls().map((call) => call.url)).toEqual([
      "/api/customers/7",
      "/api/customers/7",
      "/api/customers/7",
      "/api/customers/7",
    ]);
    const patchBodies = customersCalls()
      .filter((call) => call.init.method === "PATCH")
      .map((call) => JSON.parse((call.init as { body: string }).body));
    // The stale save goes with version 3; the reloaded one with version 9.
    expect(patchBodies).toHaveLength(2);
    expect(patchBodies[0].version).toBe(3);
    expect(patchBodies[1].version).toBe(9);
  });
});
