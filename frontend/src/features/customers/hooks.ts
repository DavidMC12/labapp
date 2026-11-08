/**
 * TanStack Query hooks of the customers module. Every hook uses
 * `retry: false`: a failed request is a user-visible state, not something
 * a retry loop hides. The keys always carry the id as a **number**, so two
 * screens that reach the same customer share one cache entry.
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
import {
  createCustomer,
  fetchCustomer,
  fetchCustomers,
  setCustomerStatus,
  updateCustomer,
  type CustomerFormValues,
  type CustomerListRequest,
  type CustomerStatusAction,
  type CustomerUpdateBody,
} from "./api";
import type { Customer, CustomerList } from "./types";

/** Prefix of every list key; used to invalidate the lists at once. */
export const CUSTOMERS_LIST_KEY = ["customers", "list"] as const;

/**
 * Key of one list query: `["customers", "list", { page, q, status }]`. An
 * empty `q` never has one of these keys, so `{ page: 1, q: "" }` and
 * `{ page: 1 }` do not split the cache in two.
 */
export function customersListQueryKey(
  params: CustomerListRequest,
): readonly [string, string, { page: number; q?: string; status?: string }] {
  return [CUSTOMERS_LIST_KEY[0], CUSTOMERS_LIST_KEY[1], {
    page: params.page,
    q: params.q || undefined,
    status: params.status || undefined,
  }];
}

/**
 * Key of one detail query. The id is a number taken from the route by
 * `parseCustomerIdParam`; a string id here would create a second, dead
 * cache entry.
 */
export function customerDetailKey(
  id: number,
): readonly [string, string, number] {
  return ["customers", "detail", id];
}

/**
 * Any 401 of the customers endpoints means "no session": it writes `null`
 * into the `["auth", "me"]` cache entry so the shell redirects to the
 * login instead of showing "Reintentar" for ever, and a 401
 * `SESSION_EXPIRED` also raises the expired flag (see `noteUnauthorized`).
 */
function note401(error: unknown, queryClient: QueryClient): void {
  noteUnauthorized(error, queryClient);
}

/** One page of the list, url state of `?page=&q=&status=`. */
export function useCustomers(
  params: CustomerListRequest,
): UseQueryResult<CustomerList, ApiRequestError> {
  const queryClient = useQueryClient();

  return useQuery<CustomerList, ApiRequestError>({
    queryKey: customersListQueryKey(params),
    queryFn: async () => {
      try {
        return await fetchCustomers(params);
      } catch (error) {
        note401(error, queryClient);
        throw error;
      }
    },
    retry: false,
  });
}

/** One customer by numeric id. */
export function useCustomer(
  id: number,
): UseQueryResult<Customer, ApiRequestError> {
  const queryClient = useQueryClient();

  return useQuery<Customer, ApiRequestError>({
    queryKey: customerDetailKey(id),
    queryFn: async () => {
      try {
        return await fetchCustomer(id);
      } catch (error) {
        note401(error, queryClient);
        throw error;
      }
    },
    retry: false,
  });
}

/** POST /api/customers. */
export function useCreateCustomer(): UseMutationResult<
  Customer,
  ApiRequestError,
  CustomerFormValues
> {
  const queryClient = useQueryClient();

  return useMutation<Customer, ApiRequestError, CustomerFormValues>({
    mutationFn: (values) => createCustomer(values),
    retry: false,
    onSuccess: (customer) => {
      queryClient.setQueryData(customerDetailKey(customer.id), customer);
      void queryClient.invalidateQueries({ queryKey: CUSTOMERS_LIST_KEY });
    },
    onError: (error) => {
      note401(error, queryClient);
    },
  });
}

/** PATCH /api/customers/{id} with all editable fields and the version. */
export function useUpdateCustomer(): UseMutationResult<
  Customer,
  ApiRequestError,
  { id: number; body: CustomerUpdateBody }
> {
  const queryClient = useQueryClient();

  return useMutation<
    Customer,
    ApiRequestError,
    { id: number; body: CustomerUpdateBody }
  >({
    mutationFn: ({ id, body }) => updateCustomer(id, body),
    retry: false,
    onSuccess: (customer, variables) => {
      queryClient.setQueryData(customerDetailKey(variables.id), customer);
      void queryClient.invalidateQueries({ queryKey: CUSTOMERS_LIST_KEY });
    },
    onError: (error) => {
      note401(error, queryClient);
    },
  });
}

/**
 * POST /api/customers/{id}/deactivate or /reactivate with the `If-Match`
 * version of the customer on screen; `version` is provided by the caller
 * at click time, from a value it refetches after every failure.
 */
export function useSetCustomerStatus(): UseMutationResult<
  Customer,
  ApiRequestError,
  { id: number; action: CustomerStatusAction; version: number }
> {
  const queryClient = useQueryClient();

  return useMutation<
    Customer,
    ApiRequestError,
    { id: number; action: CustomerStatusAction; version: number }
  >({
    mutationFn: ({ id, action, version }) =>
      setCustomerStatus(id, action, version),
    retry: false,
    onSuccess: (customer, variables) => {
      queryClient.setQueryData(customerDetailKey(variables.id), customer);
      void queryClient.invalidateQueries({ queryKey: CUSTOMERS_LIST_KEY });
    },
    onError: (error) => {
      note401(error, queryClient);
    },
  });
}
