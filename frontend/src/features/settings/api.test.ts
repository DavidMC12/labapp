import { fetchSettings, updateTaxRate } from "./api";
import { describe, expect, it, vi } from "vitest";

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

/** Reads the path and the init of the recorded call. */
function call(index: number): [string, RequestInit] {
  return fetchMock.mock.calls[index] as [string, RequestInit];
}

describe("fetchSettings", () => {
  it("calls GET /api/settings", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ tax_rate: "10.00" }), { status: 200 }),
    );

    const settings = await fetchSettings();

    expect(call(0)[0]).toBe("/api/settings");
    expect(call(0)[1].method).toBe("GET");
    expect(call(0)[1].body).toBeUndefined();
    expect(settings).toEqual({ tax_rate: "10.00" });
  });
});

describe("updateTaxRate", () => {
  it("patches exactly the typed string as the body", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ tax_rate: "7.00" }), { status: 200 }),
    );

    const settings = await updateTaxRate("7");

    expect(call(0)[0]).toBe("/api/settings");
    expect(call(0)[1].method).toBe("PATCH");
    expect(JSON.parse(String(call(0)[1].body))).toEqual({ tax_rate: "7" });
    expect(settings).toEqual({ tax_rate: "7.00" });
  });

  it("lets the server reject the raw values it does not accept", async () => {
    for (const raw of ["", " 7", "1e1", "10.123", "100.01"]) {
      fetchMock.mockReset();
      fetchMock.mockResolvedValue(
        new Response(
          JSON.stringify({
            status: 422,
            code: "VALIDATION_ERROR",
            detail: "Revisa los datos ingresados.",
            errors: [
              { field: "tax_rate", code: "INVALID_FORMAT", message: "El formato no es válido." },
            ],
          }),
          { status: 422, headers: { "content-type": "application/problem+json" } },
        ),
      );

      await expect(updateTaxRate(raw)).rejects.toMatchObject({
        problem: { status: 422, code: "VALIDATION_ERROR" },
      });
      expect(JSON.parse(String(call(0)[1].body))).toEqual({ tax_rate: raw });
    }
  });
});
