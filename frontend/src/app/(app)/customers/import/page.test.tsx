import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CustomerImportPage from "./page";

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
let meUser: Record<string, unknown> | null;
let meStatus: number;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

/** A problem document answer of the import endpoint. */
function problemResponse(
  status: number,
  code: string,
  detail: string,
  errors?: Array<{ field: string; code: string; message: string }>,
): Response {
  return jsonResponse({ status, code, detail, errors }, status);
}

/** A CSV file built in the tests (the browser would build it from the input). */
function csvFile(content: string, name = "clientes.csv"): File {
  return new File([content], name, { type: "text/csv" });
}

/** Uploads a file on the real file input, as a user would. */
async function chooseFile(file: File): Promise<void> {
  await userEvent.upload(
    screen.getByTestId("customers-import-file-input"),
    file,
  );
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  meUser = { id: 2, name: "Ventas Demo", email: "sales@labapp.test", role: "sales" };
  meStatus = 200;
  queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/auth/me") {
      return jsonResponse(meUser, meStatus);
    }
    return jsonResponse({}, 404);
  });
});

afterEach(() => {
  document.title = "LabApp";
  vi.unstubAllGlobals();
});

describe("the customers import page", () => {
  it("renders the form and its elements with the right ids", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <CustomerImportPage />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("customers-import-form")).toBeInTheDocument();
    });
    expect(document.title).toBe("Importar clientes · LabApp");
    expect(screen.getByTestId("customers-import-heading"))
      .toHaveTextContent("Importar clientes");
    expect(screen.getByTestId("customers-import-help-text")).toBeInTheDocument();
    const input = screen.getByTestId("customers-import-file-input");
    expect(input).toHaveAttribute("type", "file");
    expect(input).toHaveAttribute("accept", ".csv,text/csv");
    expect(input).toHaveAttribute("id", "customers-import-file-input");
    expect(input).toHaveAttribute(
      "aria-describedby",
      "customers-import-help-text",
    );
    expect(screen.getByLabelText("Archivo CSV")).toBe(input);
    expect(screen.getByTestId("customers-import-form")).toHaveAttribute(
      "data-state",
      "idle",
    );
    expect(screen.getByTestId("customers-import-submit-button")).toBeDisabled();
    expect(screen.getByTestId("customers-import-back-link"))
      .toHaveAttribute("href", "/customers");
  });

  it("does not render the form for finance or readonly", async () => {
    for (const [role, email] of [
      ["finance", "finance@labapp.test"],
      ["readonly", "readonly@labapp.test"],
    ] as const) {
      meUser = { id: 9, name: `${role} demo`, email, role };
      const view = render(
        <QueryClientProvider client={queryClient}>
          <CustomerImportPage />
        </QueryClientProvider>,
      );
      await waitFor(() => {
        expect(
          screen.getByTestId("customers-import-forbidden-alert"),
        ).toHaveTextContent("No tienes permiso para realizar esta acción.");
      });
      expect(
        screen.queryByTestId("customers-import-form"),
      ).not.toBeInTheDocument();
      view.unmount();
    }
  });

  /** Resolves the upload and returns the recorded request of the import. */
  async function submitFile(
    file: File,
    answer: () => Response | Promise<Response>,
  ): Promise<[string, RequestInit]> {
    render(
      <QueryClientProvider client={queryClient}>
        <CustomerImportPage />
      </QueryClientProvider>,
    );
    await screen.findByTestId("customers-import-form");
    await chooseFile(file);
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/customers/import") {
        return answer();
      }
      if (url === "/api/auth/me") {
        return jsonResponse(meUser, meStatus);
      }
      return jsonResponse({}, 404);
    });
    await userEvent.click(
      screen.getByTestId("customers-import-submit-button"),
    );
    await waitFor(() => {
      expect(fetchMock.mock.calls.some(([input]) =>
        String(input) === "/api/customers/import",
      )).toBe(true);
    });
    return fetchMock.mock.calls.find(([input]) =>
      String(input) === "/api/customers/import",
    ) as [string, RequestInit];
  }

  it("shows the success text in plural, clears the input and disables the button", async () => {
    const [, init] = await submitFile(
      csvFile("name,email\nAna García,ana@labapp.test\nBeto,beto@labapp.test\n"),
      () =>
        jsonResponse({
          created: 2,
          items: [{ id: 12 }, { id: 13 }],
        }, 201),
    );

    // The request body is a FormData with the file under `file`, and the
    // code sets no multipart Content-Type on itself.
    const body = init.body as FormData;
    expect(body).toBeInstanceOf(FormData);
    expect((body.get("file") as File).name).toBe("clientes.csv");
    const headers = init.headers as Record<string, string>;
    // The browser adds the multipart Content-Type with its boundary; the
    // code must not set one itself.
    expect(Object.keys(headers)).not.toContain("Content-Type");

    const status = screen.getByTestId("customers-import-result-text");
    expect(status).toHaveTextContent("Se importaron 2 clientes.");
    expect(status).toHaveAttribute("role", "status");
    expect(screen.getByTestId("customers-import-list-link"))
      .toHaveAttribute("href", "/customers");
    // The form goes to the observable success state, the input is cleared
    // and the button is disabled again.
    expect(screen.getByTestId("customers-import-form")).toHaveAttribute(
      "data-state",
      "success",
    );
    expect(screen.getByTestId("customers-import-file-input")).toHaveValue("");
    expect(screen.getByTestId("customers-import-submit-button")).toBeDisabled();
    expect(
      screen.queryByTestId("customers-import-error-alert"),
    ).not.toBeInTheDocument();
  });

  it("shows the success text in singular for one customer", async () => {
    await submitFile(
      csvFile("name,email\nAna García,ana@labapp.test\n"),
      () => jsonResponse({ created: 1, items: [{ id: 12 }] }, 201),
    );

    expect(screen.getByTestId("customers-import-result-text"))
      .toHaveTextContent("Se importó 1 cliente.");
  });

  it("marks the form busy while the request is in flight", async () => {
    let release: (response: Response) => void = () => {};
    const pending = new Promise<Response>((resolve) => {
      release = resolve;
    });

    render(
      <QueryClientProvider client={queryClient}>
        <CustomerImportPage />
      </QueryClientProvider>,
    );
    await screen.findByTestId("customers-import-form");
    await chooseFile(csvFile("name,email\nAna García,ana@labapp.test\n"));
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/customers/import") {
        return pending;
      }
      return jsonResponse({}, 404);
    });

    await userEvent.click(screen.getByTestId("customers-import-submit-button"));

    const form = screen.getByTestId("customers-import-form");
    const button = screen.getByTestId("customers-import-submit-button");
    await waitFor(() => {
      expect(form).toHaveAttribute("data-state", "loading");
    });
    expect(form).toHaveAttribute("aria-busy", "true");
    expect(button).toBeDisabled();

    release(jsonResponse({ created: 1, items: [{ id: 12 }] }, 201));
    await waitFor(() => {
      expect(form).toHaveAttribute("data-state", "success");
    });
    expect(form).not.toHaveAttribute("aria-busy");

    // Choosing another file returns the form to idle.
    await chooseFile(csvFile("name,email\nBeto,beto@labapp.test\n"));
    expect(form).toHaveAttribute("data-state", "idle");
  });

  it("shows the error table of a rejected file with whole-file, whole-row and column errors", async () => {
    const problems = [
      { field: "rows[2].email", code: "REQUIRED", message: "Este campo es obligatorio." },
      { field: "rows[3]", code: "INVALID_FORMAT", message: "El número de columnas no coincide." },
      { field: "file", code: "INVALID_FORMAT", message: "El archivo debe ser CSV." },
      { field: "rows[3].tax_id", code: "TOO_LONG", message: "El valor es demasiado largo." },
    ];
    await submitFile(
      csvFile("name,email\n,beto@labapp.test\nsolo-fila\ncolumna,extra\n"),
      () =>
        problemResponse(422, "VALIDATION_ERROR", "Revisa los datos ingresados.", problems),
    );

    const alert = screen.getByTestId("customers-import-error-alert");
    expect(alert).toHaveAttribute("role", "alert");
    expect(alert).toHaveTextContent(
      "El archivo tiene errores. No se importó nada.",
    );
    // The focus of a failed submit moves to the alert, and the form stays
    // in the error state.
    expect(alert).toHaveFocus();
    expect(screen.getByTestId("customers-import-form")).toHaveAttribute(
      "data-state",
      "error",
    );

    expect(screen.getByTestId("customers-import-errors-table")).toBeInTheDocument();
    expect(screen.getByTestId("customers-import-errors-table"))
      .toHaveAttribute("data-testid", "customers-import-errors-table");

    // One row per entry, in the order the API sends them.
    expect(screen.getByTestId("customers-import-error-row-1")).toBeInTheDocument();
    expect(screen.getByTestId("customers-import-error-row-2")).toBeInTheDocument();
    expect(screen.getByTestId("customers-import-error-row-3")).toBeInTheDocument();
    expect(screen.getByTestId("customers-import-error-row-4")).toBeInTheDocument();
    expect(screen.queryByTestId("customers-import-error-row-5")).not.toBeInTheDocument();

    expect(screen.getByTestId("customers-import-error-line-cell-1"))
      .toHaveTextContent("2");
    expect(screen.getByTestId("customers-import-error-field-cell-1"))
      .toHaveTextContent("Email");
    expect(screen.getByTestId("customers-import-error-message-cell-1"))
      .toHaveTextContent("Este campo es obligatorio.");

    expect(screen.getByTestId("customers-import-error-line-cell-2"))
      .toHaveTextContent("3");
    expect(screen.getByTestId("customers-import-error-field-cell-2"))
      .toHaveTextContent("Fila completa");

    expect(screen.getByTestId("customers-import-error-line-cell-3"))
      .toHaveTextContent("—");
    expect(screen.getByTestId("customers-import-error-field-cell-3"))
      .toHaveTextContent("Archivo");

    expect(screen.getByTestId("customers-import-error-line-cell-4"))
      .toHaveTextContent("3");
    expect(screen.getByTestId("customers-import-error-field-cell-4"))
      .toHaveTextContent("ID fiscal");

    // No truncation note for fewer than 100 entries.
    expect(
      screen.queryByTestId("customers-import-truncated-text"),
    ).not.toBeInTheDocument();
  });

  it("shows the field labels of the five columns in the error table", async () => {
    const problems = [
      { field: "rows[2].name", code: "REQUIRED", message: "Este campo es obligatorio." },
      { field: "rows[2].phone", code: "INVALID_FORMAT", message: "El formato no es válido." },
      { field: "rows[2].address", code: "INVALID_FORMAT", message: "El formato no es válido." },
    ];
    await submitFile(
      csvFile("name,email\n,ana@labapp.test\n"),
      () =>
        problemResponse(422, "VALIDATION_ERROR", "Revisa los datos ingresados.", problems),
    );

    expect(screen.getByTestId("customers-import-error-field-cell-1"))
      .toHaveTextContent("Nombre");
    expect(screen.getByTestId("customers-import-error-field-cell-2"))
      .toHaveTextContent("Teléfono");
    expect(screen.getByTestId("customers-import-error-field-cell-3"))
      .toHaveTextContent("Dirección");
  });

  it("shows the truncation note when the API sends exactly 100 entries", async () => {
    const problems = Array.from({ length: 100 }, (_, index) => ({
      field: `rows[${index + 2}].email`,
      code: "REQUIRED",
      message: "Este campo es obligatorio.",
    }));
    await submitFile(
      csvFile("name,email\n,ana@labapp.test\n"),
      () =>
        problemResponse(422, "VALIDATION_ERROR", "Revisa los datos ingresados.", problems),
    );

    expect(screen.getByTestId("customers-import-truncated-text"))
      .toHaveTextContent("Se muestran los primeros 100 errores.");
    expect(screen.getByTestId("customers-import-error-row-100")).toBeInTheDocument();
    expect(screen.queryByTestId("customers-import-error-row-101")).not.toBeInTheDocument();
  });

  it("shows the fixed too-large message on 413", async () => {
    await submitFile(
      csvFile("name,email\nAna García,ana@labapp.test\n", "grande.csv"),
      () =>
        problemResponse(413, "PAYLOAD_TOO_LARGE", "El cuerpo es demasiado grande."),
    );

    expect(screen.getByTestId("customers-import-error-alert")).toHaveTextContent(
      "El archivo es demasiado grande (máximo 100 KB).",
    );
    expect(
      screen.queryByTestId("customers-import-errors-table"),
    ).not.toBeInTheDocument();
  });

  it("shows the API message on 409 CUSTOMER_EMAIL_TAKEN and 403", async () => {
    for (const [status, code, detail] of [
      [409, "CUSTOMER_EMAIL_TAKEN", "Ya existe un cliente con ese email."],
      [403, "FORBIDDEN", "No tienes permiso para realizar esta acción."],
    ] as const) {
      const view = render(
        <QueryClientProvider client={queryClient}>
          <CustomerImportPage />
        </QueryClientProvider>,
      );
      await screen.findByTestId("customers-import-form");
      await chooseFile(csvFile("name,email\nAna García,ana@labapp.test\n"));
      fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/api/customers/import") {
          return problemResponse(status, code, detail);
        }
        if (url === "/api/auth/me") {
          return jsonResponse(meUser, meStatus);
        }
        return jsonResponse({}, 404);
      });
      await userEvent.click(screen.getByTestId("customers-import-submit-button"));

      await waitFor(() => {
        expect(screen.getByTestId("customers-import-error-alert"))
          .toHaveTextContent(detail);
      });
      expect(screen.getByTestId("customers-import-error-alert")).toHaveFocus();
      expect(screen.getByTestId("customers-import-form")).toHaveAttribute(
        "data-state",
        "error",
      );
      view.unmount();
    }
  });

  it("shows the generic message on a network failure", async () => {
    await submitFile(
      csvFile("name,email\nAna García,ana@labapp.test\n"),
      () => Promise.reject<Response>(new TypeError("Failed to fetch")),
    );

    expect(screen.getByTestId("customers-import-error-alert")).toHaveTextContent(
      "Ocurrió un error inesperado. Inténtalo de nuevo.",
    );
  });

  it("clears an earlier success text when a new attempt starts", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <CustomerImportPage />
      </QueryClientProvider>,
    );
    await screen.findByTestId("customers-import-form");

    // First attempt succeeds.
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/customers/import") {
        return jsonResponse({ created: 1, items: [{ id: 12 }] }, 201);
      }
      if (url === "/api/auth/me") {
        return jsonResponse(meUser, meStatus);
      }
      return jsonResponse({}, 404);
    });
    await chooseFile(csvFile("name,email\nAna García,ana@labapp.test\n"));
    await userEvent.click(screen.getByTestId("customers-import-submit-button"));
    await screen.findByTestId("customers-import-result-text");

    // Second attempt fails: the success text disappears at the start.
    await chooseFile(csvFile("name,email\n,beto@labapp.test\n"));
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/customers/import") {
        return problemResponse(422, "VALIDATION_ERROR", "Revisa los datos ingresados.", [
          { field: "rows[2].email", code: "REQUIRED", message: "Este campo es obligatorio." },
        ]);
      }
      if (url === "/api/auth/me") {
        return jsonResponse(meUser, meStatus);
      }
      return jsonResponse({}, 404);
    });
    await userEvent.click(screen.getByTestId("customers-import-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("customers-import-error-alert")).toBeInTheDocument();
    });
    expect(
      screen.queryByTestId("customers-import-result-text"),
    ).not.toBeInTheDocument();
  });

  it("invalidates the cached customer lists after a success", async () => {
    const listKey = ["customers", "list"];
    queryClient.setQueryData(listKey, {
      items: [],
      page: 1,
      page_size: 20,
      total: 0,
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    await submitFile(
      csvFile("name,email\nAna García,ana@labapp.test\n"),
      () => jsonResponse({ created: 1, items: [{ id: 12 }] }, 201),
    );

    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: listKey }),
    );
  });

  it("keeps the file after a failure so a new attempt is possible", async () => {
    await submitFile(
      csvFile("name,email\n,ana@labapp.test\n"),
      () =>
        problemResponse(422, "VALIDATION_ERROR", "Revisa los datos ingresados.", [
          { field: "rows[2].email", code: "REQUIRED", message: "Este campo es obligatorio." },
        ]),
    );

    expect(screen.getByTestId("customers-import-file-input")).not.toHaveValue("");
    expect(screen.getByTestId("customers-import-submit-button")).toBeEnabled();
  });
});
