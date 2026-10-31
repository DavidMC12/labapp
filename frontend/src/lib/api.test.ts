import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiRequestError, apiFetch } from "./api";

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  fetchMock.mockReset();
});

function jsonResponse(
  body: string,
  init: { status: number; contentType?: string } = { status: 200 },
) {
  return new Response(body, {
    status: init.status,
    headers: { "content-type": init.contentType ?? "application/json" },
  });
}

describe("apiFetch", () => {
  it("sends same-origin credentials and Accept on a GET", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(JSON.stringify({ id: 1 })),
    );

    await apiFetch("/api/auth/me");

    expect(fetchMock).toHaveBeenCalledWith("/api/auth/me", {
      method: "GET",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
      },
      body: undefined,
    });
  });

  it("sends Content-Type and the JSON body when a body is defined", async () => {
    fetchMock.mockResolvedValue(jsonResponse(JSON.stringify({ id: 1 })));

    const user = await apiFetch<{ id: number }>("/api/auth/login", {
      method: "POST",
      body: {
        email: "admin@labapp.test",
        password: "Demo-LabApp-2026!",
      },
    });

    const [, init] = fetchMock.mock.calls[0] as [
      string,
      { body: string; headers: Record<string, string> },
    ];

    expect(init.headers).toMatchObject({
      Accept: "application/json",
      "Content-Type": "application/json",
    });
    expect(JSON.parse(init.body)).toEqual({
      email: "admin@labapp.test",
      password: "Demo-LabApp-2026!",
    });
    expect(user).toEqual({ id: 1 });
  });

  it("forwards the caller headers", async () => {
    fetchMock.mockResolvedValue(jsonResponse("{}"));

    await apiFetch("/api/health", {
      headers: { "X-Test-Token": "abc" },
    });

    const [, init] = fetchMock.mock.calls[0] as [
      string,
      { headers: Record<string, string> },
    ];

    expect(init.headers).toEqual({
      Accept: "application/json",
      "X-Test-Token": "abc",
    });
  });

  it("resolves undefined on a 204", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

    const result = await apiFetch<void>("/api/auth/logout", {
      method: "POST",
    });

    expect(result).toBeUndefined();
  });

  it("resolves the parsed JSON on 2xx", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(JSON.stringify({ id: 7, name: "Admin Demo" })),
    );

    await expect(apiFetch("/api/auth/me")).resolves.toEqual({
      id: 7,
      name: "Admin Demo",
    });
  });

  it("throws the problem document on a problem answer", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        JSON.stringify({
          type: "https://labapp.example/errors/invalid-credentials",
          title: "Unauthorized",
          status: 401,
          code: "INVALID_CREDENTIALS",
          detail: "Email o contraseña incorrectos.",
        }),
        {
          status: 401,
          contentType: "application/problem+json",
        },
      ),
    );

    let error: ApiRequestError | null = null;
    try {
      await apiFetch("/api/auth/login");
    } catch (thrown) {
      error = thrown as ApiRequestError;
    }

    expect(error).toBeInstanceOf(ApiRequestError);
    expect(error?.problem).toMatchObject({
      type: "https://labapp.example/errors/invalid-credentials",
      title: "Unauthorized",
      status: 401,
      code: "INVALID_CREDENTIALS",
      detail: "Email o contraseña incorrectos.",
    });
    expect(error?.message).toBe("Email o contraseña incorrectos.");
  });

  it("counts a JSON object with code and detail as a problem document whatever the content type", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        JSON.stringify({ status: 500, code: "INTERNAL_ERROR", detail: "Ocurrió un error inesperado. Inténtalo de nuevo." }),
        { status: 500, contentType: "text/html" },
      ),
    );

    try {
      await apiFetch("/api/auth/me");
      expect.unreachable("apiFetch should have thrown");
    } catch (thrown) {
      expect(thrown).toBeInstanceOf(ApiRequestError);
      expect((thrown as ApiRequestError).problem.status).toBe(500);
      expect((thrown as ApiRequestError).problem.code).toBe("INTERNAL_ERROR");
    }
  });

  it("carries the validation errors of a 422 problem document", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        JSON.stringify({
          status: 422,
          code: "VALIDATION_ERROR",
          detail: "Revisa los datos ingresados.",
          errors: [
            { field: "email", code: "INVALID_FORMAT", message: "El formato no es válido." },
          ],
        }),
        { status: 422, contentType: "application/problem+json" },
      ),
    );

    let problem: ApiRequestError["problem"] | null = null;
    try {
      await apiFetch("/api/auth/login");
    } catch (thrown) {
      problem = (thrown as ApiRequestError).problem;
    }

    expect(problem?.errors).toEqual([
      { field: "email", code: "INVALID_FORMAT", message: "El formato no es válido." },
    ]);
  });

  it("throws a synthesized problem on a non-JSON failure", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse("<html>Proxy error</html>", {
        status: 502,
        contentType: "text/html",
      }),
    );

    try {
      await apiFetch("/api/auth/me");
      expect.unreachable("apiFetch should have thrown");
    } catch (thrown) {
      const error = thrown as ApiRequestError;
      expect(error).toBeInstanceOf(ApiRequestError);
      expect(error.problem.status).toBe(502);
      expect(error.problem.code).toBe("INTERNAL_ERROR");
      expect(error.problem.detail).toBe(
        "Ocurrió un error inesperado. Inténtalo de nuevo.",
      );
    }
  });

  it("throws a synthesized problem with status 0 when fetch rejects", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));

    try {
      await apiFetch("/api/auth/me");
      expect.unreachable("apiFetch should have thrown");
    } catch (thrown) {
      const error = thrown as ApiRequestError;
      expect(error).toBeInstanceOf(ApiRequestError);
      expect(error.problem.status).toBe(0);
      expect(error.problem.code).toBe("INTERNAL_ERROR");
      expect(error.problem.detail).toBe(
        "Ocurrió un error inesperado. Inténtalo de nuevo.",
      );
    }
  });
});
