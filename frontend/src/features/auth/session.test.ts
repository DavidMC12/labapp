import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import { ApiRequestError } from "@/lib/api";
import {
  ME_QUERY_KEY,
  SESSION_EXPIRED_QUERY_KEY,
  noteUnauthorized,
} from "./session";
import type { User } from "./types";

function apiProblem(status: number, code: string) {
  return new ApiRequestError({ status, code, detail: "detalle" });
}

const meUser = { id: 1, name: "Admin Demo" } as User;

describe("noteUnauthorized", () => {
  it("writes both cache keys on a 401 SESSION_EXPIRED", () => {
    const queryClient = new QueryClient();
    queryClient.setQueryData(ME_QUERY_KEY, meUser);

    noteUnauthorized(
      apiProblem(401, "SESSION_EXPIRED"),
      queryClient,
    );

    expect(queryClient.getQueryData(ME_QUERY_KEY)).toBeNull();
    expect(queryClient.getQueryData(SESSION_EXPIRED_QUERY_KEY)).toBe(true);
  });

  it("writes only the me key on a 401 UNAUTHENTICATED", () => {
    const queryClient = new QueryClient();
    queryClient.setQueryData(ME_QUERY_KEY, meUser);

    noteUnauthorized(
      apiProblem(401, "UNAUTHENTICATED"),
      queryClient,
    );

    expect(queryClient.getQueryData(ME_QUERY_KEY)).toBeNull();
    expect(queryClient.getQueryData(SESSION_EXPIRED_QUERY_KEY))
      .toBeUndefined();
  });

  it("changes nothing on a request error other than a 401", () => {
    const queryClient = new QueryClient();
    queryClient.setQueryData(ME_QUERY_KEY, meUser);
    queryClient.setQueryData(SESSION_EXPIRED_QUERY_KEY, true);

    noteUnauthorized(apiProblem(403, "FORBIDDEN"), queryClient);

    expect(queryClient.getQueryData(ME_QUERY_KEY)).toEqual(meUser);
    expect(queryClient.getQueryData(SESSION_EXPIRED_QUERY_KEY)).toBe(true);
  });

  it("changes nothing on an error that is not a problem document", () => {
    const queryClient = new QueryClient();
    queryClient.setQueryData(ME_QUERY_KEY, meUser);

    noteUnauthorized(new Error("boom"), queryClient);
    noteUnauthorized(undefined, queryClient);

    expect(queryClient.getQueryData(ME_QUERY_KEY)).toEqual(meUser);
    expect(queryClient.getQueryData(SESSION_EXPIRED_QUERY_KEY))
      .toBeUndefined();
  });
});
