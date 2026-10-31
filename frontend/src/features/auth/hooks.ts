import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";
import { ApiRequestError, apiFetch } from "@/lib/api";
import type { LoginInput, User } from "./types";

/**
 * Cache key of the authenticated user. `useLogin` writes the user under
 * this key *before* the page navigates, so the shell reads the fresh value
 * instead of a stale `null` left by a former 401.
 */
export const ME_QUERY_KEY = ["auth", "me"] as const;

/**
 * Current session. A 401 resolves to `null`: an expired or missing session
 * is treated as "no session" and the shell redirects silently for now. Any
 * other answer stays a rejection with the problem as its error.
 */
export function useMe(): UseQueryResult<User | null, ApiRequestError> {
  return useQuery<User | null, ApiRequestError>({
    queryKey: ME_QUERY_KEY,
    queryFn: async () => {
      try {
        return await apiFetch<User>("/api/auth/me");
      } catch (error) {
        if (error instanceof ApiRequestError && error.problem.status === 401) {
          return null;
        }
        throw error;
      }
    },
    retry: false,
  });
}

/**
 * Logs in and caches the returned user under `ME_QUERY_KEY`. FastAPI only
 * reads the body as JSON when `Content-Type: application/json` is set,
 * which `apiFetch` does because a body is defined.
 */
export function useLogin(): UseMutationResult<
  User,
  ApiRequestError,
  LoginInput
> {
  const queryClient = useQueryClient();

  return useMutation<User, ApiRequestError, LoginInput>({
    mutationFn: (input) =>
      apiFetch<User>("/api/auth/login", { method: "POST", body: input }),
    retry: false,
    onSuccess: (user) => {
      queryClient.setQueryData(ME_QUERY_KEY, user);
    },
  });
}

/**
 * Ends the session and clears the whole query cache whatever the answer
 * (success, error or network failure), so one user's cached data is never
 * shown to the next. The caller navigates to `/login` afterwards.
 */
export function useLogout(): UseMutationResult<
  void,
  ApiRequestError,
  void
> {
  const queryClient = useQueryClient();

  return useMutation<void, ApiRequestError, void>({
    mutationFn: () => apiFetch<void>("/api/auth/logout", { method: "POST" }),
    retry: false,
    onSettled: () => {
      queryClient.clear();
    },
  });
}
