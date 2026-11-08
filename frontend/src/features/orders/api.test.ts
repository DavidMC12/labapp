import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  addOrderLine,
  buildOrderListQuery,
  createOrder,
  fetchOrder,
  fetchOrders,
  fetchProducts,
  orderListUrl,
  removeOrderLine,
  setOrderCustomer,
  setOrderLineQuantity,
  transitionOrder,
} from "./api";
import type { Order } from "./types";

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

/** The literal Order of the corrected spec (S5). */
const order: Order = {
  id: 8,
  number: "PED-0008",
  status: "draft",
  customer: { id: 1, name: "Acme Industrial S.A.", status: "active" },
  lines: [
    {
      id: 10,
      product_id: 1,
      sku: "KB-100",
      name: "Teclado USB",
      quantity: 2,
      unit_price: "19.90",
      line_total: "39.80",
    },
  ],
  subtotal: "39.80",
  tax_rate: "10.00",
  tax: "3.98",
  total: "43.78",
  invoice_id: null,
  version: 2,
  created_at: "2026-11-05T15:00:00Z",
  updated_at: "2026-11-05T15:01:00Z",
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

/** Reads the path (with the query) and the init of the recorded call. */
function call(index: number): [string, RequestInit] {
  return fetchMock.mock.calls[index] as [string, RequestInit];
}

describe("buildOrderListQuery", () => {
  it("always includes page", () => {
    expect(buildOrderListQuery({ page: 3 }).toString()).toBe("page=3");
  });

  it("includes q and status only when they have a value", () => {
    expect(orderListUrl({ page: 2, q: "", status: undefined })).toBe(
      "/api/orders?page=2",
    );
    expect(orderListUrl({ page: 2, q: "ped", status: "confirmed" })).toBe(
      "/api/orders?page=2&q=ped&status=confirmed",
    );
  });

  it("encodes a q that contains reserved characters", () => {
    expect(orderListUrl({ page: 1, q: "R&D" })).toBe(
      "/api/orders?page=1&q=R%26D",
    );
  });

  it("includes customer_id only when it has a value", () => {
    expect(orderListUrl({ page: 1, customerId: undefined })).toBe(
      "/api/orders?page=1",
    );
    expect(
      orderListUrl({ page: 1, customerId: 4, q: "ped", status: "draft" }),
    ).toBe("/api/orders?page=1&q=ped&status=draft&customer_id=4");
  });

  it("carries the sort only when the request has one, with both parameters", () => {
    expect(orderListUrl({ page: 1 })).toBe("/api/orders?page=1");
    expect(
      orderListUrl({ page: 1, sort: "customer", direction: "desc" }),
    ).toBe("/api/orders?page=1&sort=customer&direction=desc");
    // A sort without a direction takes the default direction of the field.
    expect(orderListUrl({ page: 1, sort: "number" }).split("&")).toContain(
      "direction=asc",
    );
  });
});

describe("the orders requests", () => {
  it("sends the list request with the URLSearchParams query", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ items: [], page: 1, page_size: 20, total: 0 }),
    );

    await fetchOrders({ page: 2, q: "R&D", status: "draft" });

    const [path, init] = call(0);
    expect(path).toBe("/api/orders?page=2&q=R%26D&status=draft");
    expect(init.method).toBe("GET");
    expect(init.body).toBeUndefined();
  });

  it("reads one order by numeric id", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(order));

    const result = await fetchOrder(8);

    expect(call(0)[0]).toBe("/api/orders/8");
    expect(result.version).toBe(2);
  });

  it("reads the whole product catalog without paging", async () => {
    fetchMock.mockImplementation(async () =>
      jsonResponse({
        items: [
          { id: 1, sku: "KB-100", name: "Teclado USB", price: "19.90", stock: 120 },
        ],
      }));

    const result = await fetchProducts();

    expect(call(0)[0]).toBe("/api/products");
    expect(result.items[0].price).toBe("19.90");

    await fetchProducts({ sort: "price", direction: "desc" });
    expect(call(1)[0]).toBe("/api/products?sort=price&direction=desc");
  });

  it("creates a draft with the customer id as the only field", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(order, 201));

    await createOrder(1);

    const [path, init] = call(0);
    expect(path).toBe("/api/orders");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ customer_id: 1 }));
  });

  it("changes the customer of a draft with the version in the body", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(order));

    await setOrderCustomer(8, { customer_id: 2, version: 2 });

    const [path, init] = call(0);
    expect(path).toBe("/api/orders/8");
    expect(init.method).toBe("PATCH");
    expect(init.body).toBe(
      JSON.stringify({ customer_id: 2, version: 2 }),
    );
  });

  it("adds a line with product id, quantity and version", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(order, 201));

    await addOrderLine(8, { product_id: 1, quantity: 2, version: 2 });

    const [path, init] = call(0);
    expect(path).toBe("/api/orders/8/lines");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(
      JSON.stringify({ product_id: 1, quantity: 2, version: 2 }),
    );
  });

  it("sends a typed string quantity unchanged, as the server's INVALID_FORMAT case sends it", async () => {
    // Integers are strict on the server: `"5.5"` is not a number there.
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        {
          type: "about:blank",
          title: "Unprocessable Content",
          status: 422,
          code: "VALIDATION_ERROR",
          detail: "Revisa los datos ingresados.",
          errors: [
            {
              field: "quantity",
              code: "INVALID_FORMAT",
              message: "El formato no es válido.",
            },
          ],
        },
        422,
      ),
    );

    await expect(
      addOrderLine(8, { product_id: 1, quantity: "5.5", version: 2 }),
    ).rejects.toMatchObject({ problem: { code: "VALIDATION_ERROR" } });

    const [, init] = call(0);
    expect(init.body).toBe(
      JSON.stringify({ product_id: 1, quantity: "5.5", version: 2 }),
    );
  });

  it("changes a line quantity with the version in the body", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(order));

    await setOrderLineQuantity(8, 10, { quantity: 3, version: 2 });

    const [path, init] = call(0);
    expect(path).toBe("/api/orders/8/lines/10");
    expect(init.method).toBe("PATCH");
    expect(init.body).toBe(JSON.stringify({ quantity: 3, version: 2 }));
  });

  it("removes a line with DELETE and the If-Match version", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(order));

    await removeOrderLine(8, 10, 2);

    const [path, init] = call(0);
    expect(path).toBe("/api/orders/8/lines/10");
    expect(init.method).toBe("DELETE");
    expect(init.headers).toMatchObject({ "If-Match": '"2"' });
    expect(init.body).toBeUndefined();
  });

  it("posts the transitions without a body and with If-Match", async () => {
    for (const action of ["confirm", "cancel", "ship"] as const) {
      fetchMock.mockResolvedValueOnce(jsonResponse(order));

      await transitionOrder(8, action, 2);

      const [path, init] = call(action === "confirm" ? 0 : action === "cancel" ? 1 : 2);
      expect(path).toBe(`/api/orders/8/${action}`);
      expect(init.method).toBe("POST");
      expect(init.body).toBeUndefined();
      expect(init.headers).toMatchObject({ "If-Match": '"2"' });
    }
  });

  it("passes a problem document through as an ApiRequestError", async () => {
    // The literal 422 of the corrected spec (S1) for quantity 1000.
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        {
          type: "about:blank",
          title: "Unprocessable Content",
          status: 422,
          code: "VALIDATION_ERROR",
          detail: "Revisa los datos ingresados.",
          errors: [
            {
              field: "quantity",
              code: "OUT_OF_RANGE",
              message: "El valor debe estar entre 1 y 999.",
            },
          ],
        },
        422,
      ),
    );

    await expect(
      addOrderLine(8, { product_id: 1, quantity: 1000, version: 2 }),
    ).rejects.toMatchObject({
      name: "ApiRequestError",
      problem: {
        status: 422,
        code: "VALIDATION_ERROR",
        errors: [{ field: "quantity", code: "OUT_OF_RANGE" }],
      },
    });
  });
});
