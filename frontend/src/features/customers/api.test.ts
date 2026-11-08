import { describe, expect, it, vi } from "vitest";
import {
  buildCustomerListQuery,
  createCustomer,
  fetchCustomer,
  fetchCustomers,
  importCustomers,
  setCustomerStatus,
  updateCustomer,
} from "./api";

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

/** Reads the path (with the query) and the init of the recorded call. */
function call(index: number): [string, RequestInit] {
  return fetchMock.mock.calls[index] as [string, RequestInit];
}

describe("buildCustomerListQuery", () => {
  it("always includes page", () => {
    const search = buildCustomerListQuery({ page: 3 });
    expect(search.get("page")).toBe("3");
    expect(search.has("q")).toBe(false);
    expect(search.has("status")).toBe(false);
  });

  it("includes q and status only when they have a value", () => {
    expect(
      buildCustomerListQuery({ page: 2, q: "", status: undefined }).toString(),
    ).toBe("page=2");
    expect(
      buildCustomerListQuery({ page: 2, q: "ana", status: "inactive" }).toString(),
    ).toBe("page=2&q=ana&status=inactive");
  });

  it("carries the sort only when the request has one, with both parameters", () => {
    // The default order travels exactly as before the sorting existed.
    expect(
      buildCustomerListQuery({ page: 1 }).has("sort"),
    ).toBe(false);
    expect(
      buildCustomerListQuery({ page: 1 }).has("direction"),
    ).toBe(false);
    expect(
      buildCustomerListQuery({ page: 1, sort: "name", direction: "desc" })
        .toString(),
    ).toBe("page=1&sort=name&direction=desc");
    // A sort without a direction takes the default direction of the field.
    expect(
      buildCustomerListQuery({ page: 1, sort: "email" }).get("direction"),
    ).toBe("asc");
  });

  it("encodes reserved characters of q", () => {
    expect(buildCustomerListQuery({ page: 1, q: "R&D" }).toString()).toBe(
      "page=1&q=R%26D",
    );
    expect(buildCustomerListQuery({ page: 1, q: "50%" }).get("q")).toBe("50%");
  });
});

describe("fetchCustomers", () => {
  it("calls GET /api/customers with the built query", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({ items: [], page: 1, page_size: 20, total: 0 }),
        { status: 200 },
      ),
    );

    await fetchCustomers({ page: 2, q: "R&D", status: "active" });

    expect(call(0)[0]).toBe("/api/customers?page=2&q=R%26D&status=active");
    expect(call(0)[1].method).toBe("GET");
  });
});

describe("fetchCustomer", () => {
  it("calls GET /api/customers/{id}", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ id: 7 }), {
      status: 200,
    }));

    await fetchCustomer(7);

    expect(call(0)[0]).toBe("/api/customers/7");
    expect(call(0)[1].method).toBe("GET");
  });
});

describe("createCustomer", () => {
  it("posts the fields and sends null for empty optionals", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ id: 11 }), { status: 201 }),
    );

    await createCustomer({
      name: "Cafetería La Esquina",
      email: "cafe@example.test",
      phone: null,
      tax_id: null,
      address: null,
    });

    expect(call(0)[0]).toBe("/api/customers");
    expect(call(0)[1].method).toBe("POST");
    expect(JSON.parse(call(0)[1].body as string)).toEqual({
      name: "Cafetería La Esquina",
      email: "cafe@example.test",
      phone: null,
      tax_id: null,
      address: null,
    });
  });
});

describe("importCustomers", () => {
  it("posts the file as multipart under the part name file", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          created: 2,
          items: [{ id: 12 }, { id: 13 }],
        }),
        { status: 201 },
      ),
    );

    const file = new File(
      ["name,email\nAna García,ana@labapp.test\nBeto,beto@labapp.test\n"],
      "clientes.csv",
      { type: "text/csv" },
    );

    const result = await importCustomers(file);

    expect(result).toEqual({ created: 2, items: [{ id: 12 }, { id: 13 }] });
    expect(call(0)[0]).toBe("/api/customers/import");
    expect(call(0)[1].method).toBe("POST");

    const body = call(0)[1].body as FormData;
    expect(body).toBeInstanceOf(FormData);
    expect(body.get("file")).toBe(file);
    expect((body.get("file") as File).name).toBe("clientes.csv");
  });
});

describe("updateCustomer", () => {
  it("patches all five editable fields and the captured version", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ id: 7, version: 3 }), { status: 200 }),
    );

    await updateCustomer(7, {
      name: "Beta Comercial Ltda.",
      email: "beta@example.test",
      phone: "+1 555 010 0002",
      tax_id: "BETA-800456",
      address: null,
      version: 2,
    });

    expect(call(0)[0]).toBe("/api/customers/7");
    expect(call(0)[1].method).toBe("PATCH");
    expect(JSON.parse(call(0)[1].body as string)).toEqual({
      name: "Beta Comercial Ltda.",
      email: "beta@example.test",
      phone: "+1 555 010 0002",
      tax_id: "BETA-800456",
      address: null,
      version: 2,
    });
  });
});

describe("setCustomerStatus", () => {
  it.each([
    ["deactivate", "/api/customers/4/deactivate"],
    ["reactivate", "/api/customers/4/reactivate"],
  ] as const)("posts %s with a quoted If-Match version", async (action, path) => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ id: 4, version: 2 }), { status: 200 }),
    );

    await setCustomerStatus(4, action, 1);

    expect(call(0)[0]).toBe(path);
    expect(call(0)[1].method).toBe("POST");
    expect((call(0)[1].headers as Record<string, string>)["If-Match"]).toBe(
      '"1"',
    );
  });
});
