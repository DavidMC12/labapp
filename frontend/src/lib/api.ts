/**
 * Thin client for the LabApp API. Every call is same-origin (the Next.js
 * server proxies the API), expects JSON problem documents on failures, as
 * described in docs/SPEC.md section 8.
 */

export type ApiMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export type ApiFetchOptions = {
  method?: ApiMethod;
  body?: unknown;
  headers?: Record<string, string>;
};

export type ApiFieldError = {
  field: string;
  code: string;
  message: string;
};

/**
 * RFC 9457 problem document from docs/SPEC.md section 8. Any member the API
 * adds on top of the standard ones is carried as an index signature.
 */
export type ApiProblem = {
  type?: string;
  title?: string;
  status: number;
  code: string;
  detail: string;
  errors?: ApiFieldError[];
  [extra: string]: unknown;
};

export class ApiRequestError extends Error {
  readonly problem: ApiProblem;

  constructor(problem: ApiProblem) {
    super(problem.detail);
    this.name = "ApiRequestError";
    this.problem = problem;
  }
}

export const INTERNAL_ERROR_DETAIL =
  "Ocurrió un error inesperado. Inténtalo de nuevo.";

function internalProblem(status: number): ApiProblem {
  return {
    status,
    code: "INTERNAL_ERROR",
    detail: INTERNAL_ERROR_DETAIL,
  };
}

function isProblemDocument(value: unknown): value is ApiProblem {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as { code?: unknown }).code === "string" &&
    typeof (value as { detail?: unknown }).detail === "string"
  );
}

/**
 * Calls `fetch` on a relative API path with `credentials: "same-origin"`
 * and `Accept: application/json`. When `body` is defined it is sent as
 * JSON. A 2xx answer resolves with the parsed JSON (or `undefined` for a
 * 204); any other answer throws an `ApiRequestError` carrying the problem
 * document, real status and code `INTERNAL_ERROR` for bodies that are not
 * problem documents (or for a network rejection, status 0).
 */
export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const { method = "GET", body, headers = {} } = options;

  let response: Response;
  try {
    response = await fetch(path, {
      method,
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiRequestError(internalProblem(0));
  }

  if (response.ok) {
    if (response.status === 204) {
      return undefined as T;
    }
    return (await response.json()) as T;
  }

  let parsed: unknown = null;
  try {
    parsed = await response.json();
  } catch {
    parsed = null;
  }

  if (isProblemDocument(parsed)) {
    throw new ApiRequestError({
      ...parsed,
      status: typeof parsed.status === "number" ? parsed.status : response.status,
    });
  }

  throw new ApiRequestError(internalProblem(response.status));
}
