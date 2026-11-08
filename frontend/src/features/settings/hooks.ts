/**
 * TanStack Query hooks of the settings module. `retry: false` like every
 * other module: a failed request is a user-visible state. The tax rate is
 * the current rate of the drafts, so a successful change invalidates
 * every query whose key starts with "orders" and the lists read the new
 * rate on their next fetch.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";
import { ApiRequestError } from "@/lib/api";
import { noteUnauthorized } from "@/features/auth/session";
import { fetchSettings, updateTaxRate } from "./api";
import type { Settings } from "./types";

/** Key of the single settings query, shared by every screen. */
export const SETTINGS_KEY = ["settings"] as const;

/**
 * Any 401 of the settings endpoints means "no session": it writes `null`
 * into the `["auth", "me"]` cache entry so the shell redirects to the
 * login instead of showing "Reintentar" for ever, and a 401
 * `SESSION_EXPIRED` also raises the expired flag (see `noteUnauthorized`).
 */
function note401(error: unknown, queryClient: QueryClient): void {
  noteUnauthorized(error, queryClient);
}

/** GET /api/settings — the settings every role sees. */
export function useSettings(): UseQueryResult<Settings, ApiRequestError> {
  const queryClient = useQueryClient();

  return useQuery<Settings, ApiRequestError>({
    queryKey: SETTINGS_KEY,
    queryFn: async () => {
      try {
        return await fetchSettings();
      } catch (error) {
        note401(error, queryClient);
        throw error;
      }
    },
    retry: false,
  });
}

/**
 * PATCH /api/settings. On success the returned settings replace the
 * cache entry (`"7"` comes back as `"7.00"`) and every "orders" query is
 * invalidated, so the draft previews and totals pick up the new rate.
 */
export function useUpdateTaxRate(): UseMutationResult<
  Settings,
  ApiRequestError,
  string
> {
  const queryClient = useQueryClient();

  return useMutation<Settings, ApiRequestError, string>({
    mutationFn: (taxRate) => updateTaxRate(taxRate),
    retry: false,
    onSuccess: (settings) => {
      queryClient.setQueryData(SETTINGS_KEY, settings);
      void queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
    onError: (error) => {
      note401(error, queryClient);
    },
  });
}
