import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SettingsPage from "./page";

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

/** The answer of the settings requests: body, status and content type. */
type SettingsAnswer =
  | { body: unknown; status?: number; contentType?: string }
  | { failure: "network" };

let settingsAnswer: SettingsAnswer;

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

function resolveSettings(answer: SettingsAnswer): Response | Promise<Response> {
  if ("failure" in answer) {
    return Promise.reject(new TypeError("Failed to fetch"));
  }
  return jsonResponse(
    answer.body,
    answer.status ?? 200,
    answer.contentType ?? "application/json",
  );
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  meUser = { id: 1, name: "Admin Demo", email: "admin@labapp.test", role: "admin" };
  settingsAnswer = { body: { tax_rate: "10.00" } };
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
    if (url === "/api/settings") {
      return resolveSettings(settingsAnswer);
    }
    return jsonResponse(
      { status: 404, code: "NOT_FOUND", detail: "No." },
      404,
    );
  });
});

afterEach(() => {
  cleanup();
  document.title = "LabApp";
  vi.unstubAllGlobals();
});

function renderPage() {
  return render(
    <QueryClientProvider client={queryClient}>
      <SettingsPage />
    </QueryClientProvider>,
  );
}

/** Clean mount: exactly one live page at a time, waited until it loads. */
async function renderAsync(): Promise<void> {
  cleanup();
  renderPage();
  await waitFor(() => {
    expect(
      screen.getByTestId("settings-taxrate-current-text"),
    ).toHaveTextContent(/^10\.00 %$/);
  });
}

/** Types a raw value into the rate input and submits the form. */
async function typeAndSubmit(raw: string): Promise<void> {
  await renderAsync();
  const input = (screen.getByTestId(
    "settings-taxrate-input",
  ) as HTMLInputElement);
  fireEvent.change(input, { target: { value: raw } });
  expect(input.value).toBe(raw);
  fireEvent.click(screen.getByTestId("settings-taxrate-save-button"));
}

/**
 * Loads the screen and then swaps the settings answer before submitting:
 * the failure answers are only for the PATCH, not for the initial GET.
 */
async function typeAndSubmitWithAnswer(
  raw: string,
  answer: SettingsAnswer,
): Promise<void> {
  await renderAsync();
  settingsAnswer = answer;
  const input = (screen.getByTestId(
    "settings-taxrate-input",
  ) as HTMLInputElement);
  fireEvent.change(input, { target: { value: raw } });
  expect(input.value).toBe(raw);
  fireEvent.click(screen.getByTestId("settings-taxrate-save-button"));
}

const VALIDATION_PROBLEM = {
  body: {
    status: 422,
    code: "VALIDATION_ERROR",
    detail: "Revisa los datos ingresados.",
    errors: [
      {
        field: "tax_rate",
        code: "INVALID_FORMAT",
        message: "El formato no es válido.",
      },
    ],
  },
  status: 422,
  contentType: "application/problem+json",
};

describe("the settings screen views", () => {
  it("shows the current rate and the form for the admin", async () => {
    await renderAsync();

    expect(screen.getByTestId("settings-page-heading")).toHaveTextContent(
      "Configuración",
    );
    // The tab answers "Configuración · LabApp" (useDocumentTitle).
    expect(document.title).toBe("Configuración · LabApp");
    expect(screen.getByTestId("settings-taxrate-heading")).toHaveTextContent(
      "Impuesto",
    );
    expect(screen.getByTestId("settings-taxrate-current-text"))
      .toHaveTextContent("10.00 %");

    const input = (screen.getByTestId(
      "settings-taxrate-input",
    ) as HTMLInputElement);
    expect(input.value).toBe("10.00");
    expect(input.getAttribute("type")).toBe("text");
    expect(input.getAttribute("inputMode")).toBe("decimal");
    expect(
      screen.getByTestId("settings-taxrate-save-button"),
    ).toHaveTextContent("Guardar");
    expect(document.querySelector("form")).toHaveAttribute("noValidate");
  });

  it("shows no form and the readonly sentence for every other role", async () => {
    for (const role of ["sales", "finance", "readonly"] as const) {
      meUser = {
        id: 2,
        name: "Demo",
        email: "demo@labapp.test",
        role,
      };

      await renderAsync();

      expect(screen.getByTestId("settings-taxrate-current-text"))
        .toHaveTextContent("10.00 %");
      expect(
        screen.getByTestId("settings-taxrate-readonly-text"),
      ).toHaveTextContent("Solo un administrador puede cambiar el impuesto.");
      expect(
        screen.queryByTestId("settings-taxrate-form"),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId("settings-taxrate-input"),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId("settings-taxrate-save-button"),
      ).not.toBeInTheDocument();
    }
  });

  it("shows a busy status while the settings load", async () => {
    cleanup();
    fetchMock.mockImplementation(
      (input: RequestInfo | URL) =>
        String(input) === "/api/settings"
          ? new Promise<Response>(() => {})
          : jsonResponse(meUser, 200),
    );
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("settings-page-loading-status"))
        .toHaveTextContent("Cargando configuración…");
    });
    expect(screen.getByTestId("settings-page-loading-status")).toHaveAttribute(
      "aria-busy",
      "true",
    );
  });

  it("shows an alert with a retry button when the load fails", async () => {
    settingsAnswer = {
      body: {
        status: 500,
        code: "INTERNAL_ERROR",
        detail: "Fallo del servidor.",
      },
      status: 500,
      contentType: "application/problem+json",
    };

    cleanup();
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("settings-page-error-alert"))
        .toHaveTextContent("Fallo del servidor.");
    });
    expect(screen.getByTestId("settings-page-retry-button"))
      .toHaveTextContent("Reintentar");

    // The retry recovers the screen.
    settingsAnswer = { body: { tax_rate: "10.00" } };
    fireEvent.click(screen.getByTestId("settings-page-retry-button"));

    await waitFor(() => {
      expect(
        screen.getByTestId("settings-taxrate-current-text"),
      ).toHaveTextContent("10.00 %");
    });
  });
});

describe("the tax rate requests", () => {
  it("requests GET /api/settings", async () => {
    await renderAsync();

    expect(
      fetchMock.mock.calls.some(
        (entry) =>
          entry[0] === "/api/settings" && entry[1].method === "GET",
      ),
    ).toBe(true);
  });

  it("patches the raw value exactly as typed for every checked value", async () => {
    const raws = ["7", " 7", "1e1", "10.123", "", "100", "100.01"];

    for (const raw of raws) {
      // One isolated page per value: the requests of the previous value
      // must not be mixed into this one.
      fetchMock.mockClear();
      settingsAnswer = { body: { tax_rate: "10.00" } };

      await typeAndSubmit(raw);

      const patchCalls = fetchMock.mock.calls.filter(
        (entry) => entry[1].method === "PATCH",
      );
      expect(patchCalls).toHaveLength(1);
      const [path, init] = patchCalls[0] as [string, RequestInit];
      expect(path).toBe("/api/settings");
      expect(init.headers).toMatchObject(
        expect.objectContaining({ "Content-Type": "application/json" }),
      );
      expect(JSON.parse(String(init.body))).toEqual({ tax_rate: raw });
      expect(patchBody(0)).toContain(raw === "" ? '""' : JSON.stringify(raw));
    }
  });
});

function patchBody(callIndex: number): string {
  const patch = fetchMock.mock.calls.filter(
    (entry) => entry[1].method === "PATCH",
  )[callIndex];
  return String(patch?.[1].body);
}

describe("the answers of the tax rate form", () => {
  it("shows a 422 INVALID_FORMAT next to the field", async () => {
    await typeAndSubmitWithAnswer("1e1", VALIDATION_PROBLEM);

    const error = await screen.findByTestId("settings-taxrate-error");
    expect(error).toHaveTextContent("El formato no es válido.");
    expect(error).toHaveAttribute("role", "alert");
    expect(screen.queryByTestId("settings-taxrate-alert")).not
      .toBeInTheDocument();
    // The focus goes to the first (only) error: the input.
    expect(document.activeElement).toBe(
      screen.getByTestId("settings-taxrate-input"),
    );
  });

  it("shows a 422 OUT_OF_RANGE next to the field", async () => {
    await typeAndSubmitWithAnswer("100.01", {
      body: {
        status: 422,
        code: "VALIDATION_ERROR",
        detail: "Revisa los datos ingresados.",
        errors: [
          {
            field: "tax_rate",
            code: "OUT_OF_RANGE",
            message: "El valor debe estar entre 0 y 100.",
          },
        ],
      },
      status: 422,
      contentType: "application/problem+json",
    });

    expect(await screen.findByTestId("settings-taxrate-error"))
      .toHaveTextContent("El valor debe estar entre 0 y 100.");
  });

  it("shows a 403 in the form alert with its detail", async () => {
    await typeAndSubmitWithAnswer("7", {
      body: {
        status: 403,
        code: "FORBIDDEN",
        detail: "No tienes permiso para realizar esta acción.",
      },
      status: 403,
      contentType: "application/problem+json",
    });

    const alert = await screen.findByTestId("settings-taxrate-alert");
    expect(alert).toHaveTextContent(
      "No tienes permiso para realizar esta acción.",
    );
    expect(alert).toHaveAttribute("role", "alert");
    expect(screen.queryByTestId("settings-taxrate-error")).not
      .toBeInTheDocument();
    expect(document.activeElement).toBe(alert);
  });

  it("shows a 500 and a network failure in the form alert", async () => {
    for (const failure of [true, false]) {
      settingsAnswer = { body: { tax_rate: "10.00" } };
      await renderAsync();

      settingsAnswer = failure
        ? {
            body: {
              status: 500,
              code: "INTERNAL_ERROR",
              detail: "Fallo del servidor.",
            },
            status: 500,
            contentType: "application/problem+json",
          }
        : { failure: "network" };

      const typed = (screen.getByTestId(
        "settings-taxrate-input",
      ) as HTMLInputElement);
      fireEvent.change(typed, { target: { value: "7" } });
      fireEvent.click(screen.getByTestId("settings-taxrate-save-button"));

      const alert = await screen.findByTestId("settings-taxrate-alert");
      expect(alert).toHaveTextContent(
        failure
          ? "Fallo del servidor."
          : "Ocurrió un error inesperado. Inténtalo de nuevo.",
      );
    }
  });

  it("keeps the returned value in the input, clears the errors and announces the success", async () => {
    await typeAndSubmitWithAnswer("9.999", VALIDATION_PROBLEM);
    expect(await screen.findByTestId("settings-taxrate-error"))
      .toHaveTextContent("El formato no es válido.");

    // The next attempt is valid and returns "7.00" for the typed "7".
    settingsAnswer = { body: { tax_rate: "7.00" } };
    const input = (screen.getByTestId(
      "settings-taxrate-input",
    ) as HTMLInputElement);
    fireEvent.change(input, { target: { value: "7" } });
    fireEvent.click(screen.getByTestId("settings-taxrate-save-button"));

    const status = await screen.findByTestId("settings-taxrate-success-status");
    expect(status).toHaveTextContent("Impuesto actualizado a 7.00 %.");
    expect(status).toHaveAttribute("role", "status");
    expect(
      (screen.getByTestId("settings-taxrate-input") as HTMLInputElement).value,
    ).toBe("7.00");
    expect(screen.queryByTestId("settings-taxrate-error")).not
      .toBeInTheDocument();

    // The current rate and the cache follow the answer.
    expect(screen.getByTestId("settings-taxrate-current-text"))
      .toHaveTextContent("7.00 %");
    expect(queryClient.getQueryData(["settings"])).toEqual({
      tax_rate: "7.00",
    });
  });

  it("invalidates every orders query on success", async () => {
    const ordersListKey = ["orders", "list", { page: 1 }];
    const ordersDetailKey = ["orders", "detail", 8];
    queryClient.setQueryData(ordersListKey, { note: "list" });
    queryClient.setQueryData(ordersDetailKey, { note: "detail" });

    await renderAsync();

    settingsAnswer = { body: { tax_rate: "7.00" } };
    const input = (screen.getByTestId(
      "settings-taxrate-input",
    ) as HTMLInputElement);
    fireEvent.change(input, { target: { value: "7" } });
    fireEvent.click(screen.getByTestId("settings-taxrate-save-button"));

    await screen.findByTestId("settings-taxrate-success-status");
    await waitFor(() => {
      expect(
        queryClient.getQueryState(ordersListKey)?.isInvalidated,
      ).toBe(true);
      expect(
        queryClient.getQueryState(ordersDetailKey)?.isInvalidated,
      ).toBe(true);
    });
  });

  it("ignores a second click while the first request runs", async () => {
    cleanup();
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/auth/me") {
        return jsonResponse(meUser, 200);
      }
      if (url === "/api/settings") {
        return new Promise<Response>((resolve) => {
          setTimeout(() => resolve(jsonResponse({ tax_rate: "10.00" }, 200)), 50);
        });
      }
      return jsonResponse({}, 404);
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("settings-taxrate-current-text"))
        .toBeInTheDocument();
    });
    const input = screen.getByTestId("settings-taxrate-input");
    fireEvent.change(input, { target: { value: "7" } });
    const button = screen.getByTestId("settings-taxrate-save-button");
    fireEvent.click(button);
    fireEvent.click(button);

    await screen.findByTestId("settings-taxrate-success-status");
    expect(patchBody(0)).toBe(JSON.stringify({ tax_rate: "7" }));
    expect(
      fetchMock.mock.calls.filter((entry) => entry[1].method === "PATCH"),
    ).toHaveLength(1);
  });
});
