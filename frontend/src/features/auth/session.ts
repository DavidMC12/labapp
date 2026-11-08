/**
 * Cache keys and 401 bookkeeping of the session, shared by every module
 * (`useMe` here, and the `note401` helpers of customers, orders, invoices
 * and settings).
 *
 * The two keys live together in this file because they are written at the
 * same time: a 401 answers "no session" and, when the session expired,
 * also asks the next login to show why. `useLogin` exports the me key and
 * clears the expired flag.
 */

import type { QueryClient } from "@tanstack/react-query";
import { ApiRequestError } from "@/lib/api";

/**
 * Cache key of the authenticated user. Re-exported by
 * `@/features/auth/hooks`, which writes the user under this key *before*
 * the page navigates, so the shell reads the fresh value instead of a
 * stale `null` left by a former 401.
 */
export const ME_QUERY_KEY = ["auth", "me"] as const;

/**
 * Cache key of the expired-session flag written by `noteUnauthorized`
 * and read by the shell to point the redirect at
 * `/login?expired=1`. `useLogin` clears it on a successful login.
 */
export const SESSION_EXPIRED_QUERY_KEY = ["auth", "session-expired"] as
  const;

/**
 * Notes a 401 in the query cache. A 401 of any endpoint means "no
 * session": it writes `null` into the `["auth", "me"]` cache entry so the
 * shell redirects to the login instead of showing "Reintentar" for ever.
 * A 401 `SESSION_EXPIRED` additionally sets the flag under
 * `SESSION_EXPIRED_QUERY_KEY`, so the shell sends the user to
 * `/login?expired=1` and the login page can say why it is there. Every
 * other error, and every error that is not a problem document, changes
 * nothing.
 */
export function noteUnauthorized(
  error: unknown,
  queryClient: QueryClient,
): void {
  if (error instanceof ApiRequestError && error.problem.status === 401) {
    if (error.problem.code === "SESSION_EXPIRED") {
      queryClient.setQueryData(SESSION_EXPIRED_QUERY_KEY, true);
    }
    queryClient.setQueryData(ME_QUERY_KEY, null);
  }
}
