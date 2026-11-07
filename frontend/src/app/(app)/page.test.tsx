import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import HomePage from "./page";
import { isValidTestId, type TestId } from "@/lib/testid";

const state = vi.hoisted(() => ({
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
  useRouter: () => state.router,
}));

const fetchMock = vi.fn();

let queryClient: QueryClient;

/** Who the mocked /api/auth/me answers. */
let meUser: { id: number; name: string; email: string; role: string } | null;

/** Answers per list url; `null` resolves never (loading). */
let listAnswers: Record<string, { total: number } | "fail" | "never" | undefined> = {};

/** The counters the brief fixes, with the statuses of each group. */
const COUNTERS = [
  ["customers", ["active", "inactive"]],
  ["orders", ["draft", "confirmed", "paid", "shipped", "cancelled"]],
  ["invoices", ["issued", "paid", "void"]],
] as const;

function jsonResponse(
  body: unknown,
  status = 200,
  contentType = "application/json",
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": contentType },
  });
}

function defaultListAnswer(url: string): Response {
  // Every list url exists in the seed story: give each a distinct total
  // derived from the status, so tests can tell the counters apart.
  // (Relative urls have no base for `new URL`, so read the query
  // directly.)
  const status = /status=([a-z]+)/.exec(url)?.[1] ?? "all";
  let total = 0;
  for (const character of status) {
    total = total * 7 + character.charCodeAt(0);
    total = total % 97;
  }
  return jsonResponse({ items: [], page: 1, page_size: 20, total: total + 1 });
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  meUser = { id: 1, name: "Admin Demo", email: "admin@labapp.test", role: "admin" };
  listAnswers = {};
  queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/auth/me") {
      return jsonResponse(meUser, 200);
    }
    const answer = listAnswers[url];
    if (answer === "never") {
      return new Promise<Response>(() => {});
    }
    if (answer === "fail") {
      return jsonResponse(
        { status: 500, code: "INTERNAL_ERROR", detail: "Fallo del servidor." },
        500,
        "application/problem+json",
      );
    }
    if (answer !== undefined) {
      return jsonResponse(
        { items: [], page: 1, page_size: 20, total: answer.total },
      );
    }
    return defaultListAnswer(url);
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function renderPage() {
  return render(
    <QueryClientProvider client={queryClient}>
      <HomePage />
    </QueryClientProvider>,
  );
}

/** The list urls of the summary, grouped, as the list screens read them. */
function expectedUrls(): string[] {
  return [
    "/api/customers?page=1&status=active",
    "/api/customers?page=1&status=inactive",
    ...["draft", "confirmed", "paid", "shipped", "cancelled"].map(
      (status) => `/api/orders?page=1&status=${status}`,
    ),
    ...["issued", "paid", "void"].map(
      (status) => `/api/invoices?page=1&status=${status}`,
    ),
  ];
}

describe("the home summary structure", () => {
  it("shows the heading, the greeting with the role label and the sections", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("app-home-greeting-text")).toHaveTextContent(
        "Hola, Admin Demo · Admin",
      );
    });

    expect(screen.getByTestId("app-home-heading")).toHaveTextContent(
      "Resumen",
    );
    for (const heading of [
      "home-customers-heading",
      "home-orders-heading",
      "home-invoices-heading",
    ]) {
      expect(screen.getByTestId(heading)).toBeInTheDocument();
    }
  });
  it("requests exactly the ten filtered lists of page 1", async () => {
    meUser = null;
    meUser = { id: 2, name: "Demo", email: "demo@labapp.test", role: "sales" };

    renderPage();

    await waitFor(() => {
      for (const url of expectedUrls()) {
        expect(
          fetchMock.mock.calls.some((entry) => entry[0] === url),
        ).toBe(true);
      }
    });
    // Nothing else is requested by the summary itself.
    const nonList = fetchMock.mock.calls.filter(
      (entry) => entry[0] !== "/api/auth/me" && !expectedUrls().includes(String(entry[0])),
    );
    expect(nonList).toHaveLength(0);
  });

  it("renders every counter from the total of its request", async () => {
    const totals: Record<string, number> = {
      "/api/customers?page=1&status=active": 12,
      "/api/customers?page=1&status=inactive": 3,
      "/api/orders?page=1&status=draft": 1,
      "/api/orders?page=1&status=confirmed": 4,
      "/api/orders?page=1&status=paid": 2,
      "/api/orders?page=1&status=shipped": 0,
      "/api/orders?page=1&status=cancelled": 9,
      "/api/invoices?page=1&status=issued": 5,
      "/api/invoices?page=1&status=paid": 5,
      "/api/invoices?page=1&status=void": 1,
    };
    listAnswers = Object.fromEntries(
      Object.entries(totals).map(([url, total]) => [url, { total }]),
    );

    renderPage();

    for (const [url, total] of Object.entries(totals)) {
      const status = /status=([a-z]+)/.exec(url)?.[1] ?? "";
      const group = url.includes("/api/customers")
        ? "customers"
        : url.includes("/api/orders")
        ? "orders"
        : "invoices";
      await waitFor(() => {
        expect(
          screen.getByTestId(`home-${group}-${status}-count-text`),
        ).toHaveTextContent(new Intl.NumberFormat("es-US").format(total));
      });
    }
  });

  it("links each counter to the filtered list the screen reads", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("home-customers-active-link")).toHaveAttribute(
        "href",
        "/customers?status=active",
      );
    });

    const links: [TestId, string][] = [
      ["home-customers-active-link", "/customers?status=active"],
      ["home-customers-inactive-link", "/customers?status=inactive"],
      ["home-orders-draft-link", "/orders?status=draft"],
      ["home-orders-confirmed-link", "/orders?status=confirmed"],
      ["home-orders-paid-link", "/orders?status=paid"],
      ["home-orders-shipped-link", "/orders?status=shipped"],
      ["home-orders-cancelled-link", "/orders?status=cancelled"],
      ["home-invoices-issued-link", "/invoices?status=issued"],
      ["home-invoices-paid-link", "/invoices?status=paid"],
      ["home-invoices-void-link", "/invoices?status=void"],
    ];
    for (const [testId, href] of links) {
      expect(screen.getByTestId(testId)).toHaveAttribute("href", href);
    }
  });

  it("labels the counters with the label helpers of the modules", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("home-customers-active-link")).toHaveTextContent(
        "Activo",
      );
    });
    expect(
      screen.getByTestId("home-customers-inactive-link"),
    ).toHaveTextContent("Inactivo");
    expect(screen.getByTestId("home-orders-draft-link")).toHaveTextContent(
      "Borrador",
    );
    expect(screen.getByTestId("home-orders-confirmed-link")).toHaveTextContent(
      "Confirmado",
    );
    expect(screen.getByTestId("home-orders-paid-link")).toHaveTextContent(
      "Pagado",
    );
    expect(screen.getByTestId("home-orders-shipped-link")).toHaveTextContent(
      "Enviado",
    );
    expect(screen.getByTestId("home-orders-cancelled-link")).toHaveTextContent(
      "Cancelado",
    );
    expect(screen.getByTestId("home-invoices-issued-link")).toHaveTextContent(
      "Emitida",
    );
    expect(screen.getByTestId("home-invoices-paid-link")).toHaveTextContent(
      "Pagada",
    );
    expect(screen.getByTestId("home-invoices-void-link")).toHaveTextContent(
      "Anulada",
    );
  });
});

describe("the home summary states", () => {
  it("shows the busy status in place of the number while a counter loads", async () => {
    listAnswers = {
      "/api/orders?page=1&status=confirmed": "never",
    };

    renderPage();

    await waitFor(() => {
      expect(
        screen.getByTestId("home-orders-confirmed-loading-status"),
      ).toHaveTextContent("Cargando…");
    });
    // The same counter has no count on screen yet; the neighbours render
    // as their requests land.
    expect(
      screen.queryByTestId("home-orders-confirmed-count-text"),
    ).not.toBeInTheDocument();
    await waitFor(() => {
      expect(
        screen.getByTestId("home-orders-draft-count-text"),
      ).toBeInTheDocument();
      expect(
        screen.getByTestId("home-customers-active-count-text"),
      ).toBeInTheDocument();
    });
  });

  it("keeps the other groups when one group fails and offers its retry", async () => {
    listAnswers = {
      "/api/invoices?page=1&status=issued": "fail",
      "/api/invoices?page=1&status=paid": "fail",
      "/api/invoices?page=1&status=void": "fail",
    };

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("home-invoices-retry-button")).toHaveTextContent(
        "Reintentar",
      );
    });
    // Every failed counter shows "—", never a blank card.
    for (const status of ["issued", "paid", "void"]) {
      expect(
        screen.getByTestId(`home-invoices-${status}-count-text`),
      ).toHaveTextContent("—");
      expect(
        screen.getByTestId(`home-invoices-${status}-link`),
      ).toBeInTheDocument();
    }
    // The failing group breaks only its own card.
    expect(
      screen.getByTestId("home-customers-active-count-text"),
    ).toHaveTextContent(/\d/);
    expect(
      screen.getByTestId("home-orders-draft-count-text"),
    ).toHaveTextContent(/\d/);
    // No retry button for the healthy groups.
    expect(
      screen.queryByTestId("home-customers-retry-button"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("home-orders-retry-button"),
    ).not.toBeInTheDocument();
  });

  it("recovers the failed group with its retry button", async () => {
    listAnswers = {
      "/api/customers?page=1&status=active": "fail",
      "/api/customers?page=1&status=inactive": "fail",
    };

    renderPage();

    await waitFor(() => {
      expect(
        screen.getByTestId("home-customers-retry-button"),
      ).toHaveTextContent("Reintentar");
    });
    expect(
      screen.getByTestId("home-customers-active-count-text"),
    ).toHaveTextContent("—");

    listAnswers = {};
    fireEvent.click(screen.getByTestId("home-customers-retry-button"));

    await waitFor(() => {
      expect(
        screen.queryByTestId("home-customers-retry-button"),
      ).not.toBeInTheDocument();
    });
    expect(
      screen.getByTestId("home-customers-active-count-text"),
    ).toHaveTextContent(/\d/);
  });

  it("writes null into the me key on a 401 of a list", async () => {
    // The me query stays in flight, so the only writes to the me key are
    // the ones the 401s produce (a 200 of me arriving later could win).
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/auth/me") {
        return new Promise<Response>(() => {});
      }
      return jsonResponse(
        { status: 401, code: "UNAUTHENTICATED", detail: "Inicia sesión." },
        401,
        "application/problem+json",
      );
    });
    queryClient.setQueryData(["auth", "me"], {
      id: 1,
      name: "Admin Demo",
      role: "admin",
    });

    renderPage();

    await waitFor(() => {
      expect(queryClient.getQueryData(["auth", "me"])).toBeNull();
    });
  });
});

describe("the greeting of the home summary", () => {
  const cases = [
    { role: "admin", label: "Admin" },
    { role: "sales", label: "Ventas" },
    { role: "finance", label: "Finanzas" },
    { role: "readonly", label: "Solo lectura" },
  ] as const;

  for (const { role, label } of cases) {
    it(`greets with the role label for ${role}`, async () => {
      meUser = {
        id: 3,
        name: "Persona Demo",
        email: "demo@labapp.test",
        role,
      };

      renderPage();

      await waitFor(() => {
        expect(screen.getByTestId("app-home-greeting-text"))
          .toHaveTextContent(`Hola, Persona Demo · ${label}`);
      });
    });
  }
});

describe("the test ids of the home summary", () => {
  const REQUIRED_IDS: readonly TestId[] = [
    "app-home-heading",
    "app-home-greeting-text",
    "home-customers-heading",
    "home-orders-heading",
    "home-invoices-heading",
    "home-customers-retry-button",
    "home-orders-retry-button",
    "home-invoices-retry-button",
    ...COUNTERS.flatMap(([group, statuses]) =>
      statuses.flatMap((status) => [
        `home-${group}-${status}-link`,
        `home-${group}-${status}-count-text`,
        `home-${group}-${status}-loading-status`,
      ] satisfies TestId[]),
    ),
  ] as readonly TestId[];

  it("makes every id valid and unique", () => {
    expect(new Set(REQUIRED_IDS).size).toBe(REQUIRED_IDS.length);
    for (const id of REQUIRED_IDS) {
      expect(isValidTestId(id), id).toBe(true);
    }
  });

  it("renders every id of the table on the loaded page", async () => {
    // Healthy render: every id except the retry buttons (which only
    // exist while a group has failed).
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("app-home-greeting-text"))
        .toBeInTheDocument();
      expect(screen.getByTestId("home-invoices-void-count-text"))
        .toBeInTheDocument();
    });

    const healthyIds: readonly TestId[] = [
      "app-home-heading",
      "app-home-greeting-text",
      "home-customers-heading",
      "home-orders-heading",
      "home-invoices-heading",
      ...COUNTERS.flatMap(([group, statuses]) =>
        statuses.flatMap((status) => [
          `home-${group}-${status}-link`,
          `home-${group}-${status}-count-text`,
        ] satisfies TestId[]),
      ),
    ] as readonly TestId[];

    // Uniqueness on the rendered page: every id is used exactly once.
    for (const id of healthyIds) {
      const rendered =
        document.querySelectorAll(`[data-testid="${id}"]`).length;
      expect(rendered, id).toBe(1);
    }

    // Failed render: each group shows its retry button.
    cleanup();
    for (const [group, statuses] of COUNTERS) {
      for (const status of statuses) {
        listAnswers[`/api/${group}?page=1&status=${status}`] = "fail";
      }
    }
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("home-customers-retry-button"))
        .toHaveTextContent("Reintentar");
      expect(screen.getByTestId("home-orders-retry-button"))
        .toBeInTheDocument();
      expect(screen.getByTestId("home-invoices-retry-button"))
        .toBeInTheDocument();
    });
  });
});
