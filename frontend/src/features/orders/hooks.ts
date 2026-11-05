/**
 * TanStack Query hooks of the orders module. Every hook uses
 * `retry: false`: a failed request is a user-visible state, not something
 * a retry loop hides. The keys always carry the id as a **number**, so the
 * place where a mutation writes the order is the entry the detail screen
 * reads.
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
import { ME_QUERY_KEY } from "@/features/auth/hooks";
import {
  addOrderLine,
  createOrder,
  fetchOrder,
  fetchOrders,
  fetchProducts,
  removeOrderLine,
  setOrderCustomer,
  setOrderLineQuantity,
  transitionOrder,
  type OrderCustomerBody,
  type OrderLineBody,
  type OrderListRequest,
  type OrderTransitionAction,
} from "./api";
import type { Order, OrderList, Product } from "./types";

/** Prefix of every list key; used to invalidate the lists at once. */
export const ORDERS_LIST_KEY = ["orders", "list"] as const;

/** Key of the product catalog. Stock changes on confirm and cancel. */
export const PRODUCTS_KEY = ["products"] as const;

/**
 * Key of one list query: `["orders", "list", { page, q, status }]`. An
 * empty `q` never has one of these keys, so `{ page: 1, q: "" }` and
 * `{ page: 1 }` do not split the cache in two.
 */
export function ordersListQueryKey(
  params: OrderListRequest,
): readonly [string, string, { page: number; q?: string; status?: string }] {
  return [ORDERS_LIST_KEY[0], ORDERS_LIST_KEY[1], {
    page: params.page,
    q: params.q || undefined,
    status: params.status || undefined,
  }];
}

/**
 * Key of one detail query. The id is a number taken from the route by
 * `parseOrderIdParam`; a string id here would create a second, dead cache
 * entry.
 */
export function orderDetailKey(id: number): readonly [string, string, number] {
  return ["orders", "detail", id];
}

/**
 * Any 401 of the orders or products endpoints means "no session": it
 * writes `null` into the `["auth", "me"]` cache entry so the shell
 * redirects to the login instead of showing "Reintentar" for ever.
 */
function note401(error: unknown, queryClient: QueryClient): void {
  if (error instanceof ApiRequestError && error.problem.status === 401) {
    queryClient.setQueryData(ME_QUERY_KEY, null);
  }
}

/** One page of the orders list, url state of `?page=&q=&status=`. */
export function useOrders(
  params: OrderListRequest,
): UseQueryResult<OrderList, ApiRequestError> {
  const queryClient = useQueryClient();

  return useQuery<OrderList, ApiRequestError>({
    queryKey: ordersListQueryKey(params),
    queryFn: async () => {
      try {
        return await fetchOrders(params);
      } catch (error) {
        note401(error, queryClient);
        throw error;
      }
    },
    retry: false,
  });
}

/** One order by numeric id. */
export function useOrder(
  id: number,
): UseQueryResult<Order, ApiRequestError> {
  const queryClient = useQueryClient();

  return useQuery<Order, ApiRequestError>({
    queryKey: orderDetailKey(id),
    queryFn: async () => {
      try {
        return await fetchOrder(id);
      } catch (error) {
        note401(error, queryClient);
        throw error;
      }
    },
    retry: false,
  });
}

/** The whole product catalog, no paging. */
export function useProducts(): UseQueryResult<
  { items: Product[] },
  ApiRequestError
> {
  const queryClient = useQueryClient();

  return useQuery<{ items: Product[] }, ApiRequestError>({
    queryKey: PRODUCTS_KEY,
    queryFn: async () => {
      try {
        return await fetchProducts();
      } catch (error) {
        note401(error, queryClient);
        throw error;
      }
    },
    retry: false,
  });
}

/**
 * Writes a mutation answer into the detail cache and invalidates the
 * derived data: the list always, and the stock for confirm and cancel.
 */
function afterOrderChange(
  queryClient: QueryClient,
  order: Order,
  options: { products?: boolean } = {},
): void {
  queryClient.setQueryData(orderDetailKey(order.id), order);
  void queryClient.invalidateQueries({ queryKey: ORDERS_LIST_KEY });
  if (options.products) {
    void queryClient.invalidateQueries({ queryKey: PRODUCTS_KEY });
  }
}

/** POST /api/orders with `{customer_id}`. */
export function useCreateOrder(): UseMutationResult<
  Order,
  ApiRequestError,
  number
> {
  const queryClient = useQueryClient();

  return useMutation<Order, ApiRequestError, number>({
    mutationFn: (customerId) => createOrder(customerId),
    retry: false,
    onSuccess: (order) => {
      afterOrderChange(queryClient, order);
    },
    onError: (error) => {
      note401(error, queryClient);
    },
  });
}

/** PATCH /api/orders/{id}: change the customer of a draft. */
export function useSetOrderCustomer(): UseMutationResult<
  Order,
  ApiRequestError,
  { id: number; body: OrderCustomerBody }
> {
  const queryClient = useQueryClient();

  return useMutation<
    Order,
    ApiRequestError,
    { id: number; body: OrderCustomerBody }
  >({
    mutationFn: ({ id, body }) => setOrderCustomer(id, body),
    retry: false,
    onSuccess: (order) => {
      afterOrderChange(queryClient, order);
    },
    onError: (error) => {
      note401(error, queryClient);
    },
  });
}

/** POST /api/orders/{id}/lines. */
export function useAddLine(): UseMutationResult<
  Order,
  ApiRequestError,
  { id: number; body: OrderLineBody & { product_id: number } }
> {
  const queryClient = useQueryClient();

  return useMutation<
    Order,
    ApiRequestError,
    { id: number; body: OrderLineBody & { product_id: number } }
  >({
    mutationFn: ({ id, body }) => addOrderLine(id, body),
    retry: false,
    onSuccess: (order) => {
      afterOrderChange(queryClient, order);
    },
    onError: (error) => {
      note401(error, queryClient);
    },
  });
}

/** PATCH /api/orders/{id}/lines/{lineId}. */
export function useSetLineQuantity(): UseMutationResult<
  Order,
  ApiRequestError,
  { id: number; lineId: number; body: OrderLineBody }
> {
  const queryClient = useQueryClient();

  return useMutation<
    Order,
    ApiRequestError,
    { id: number; lineId: number; body: OrderLineBody }
  >({
    mutationFn: ({ id, lineId, body }) => setOrderLineQuantity(id, lineId, body),
    retry: false,
    onSuccess: (order) => {
      afterOrderChange(queryClient, order);
    },
    onError: (error) => {
      note401(error, queryClient);
    },
  });
}

/** DELETE /api/orders/{id}/lines/{lineId} with `If-Match`. */
export function useRemoveLine(): UseMutationResult<
  Order,
  ApiRequestError,
  { id: number; lineId: number; version: number }
> {
  const queryClient = useQueryClient();

  return useMutation<
    Order,
    ApiRequestError,
    { id: number; lineId: number; version: number }
  >({
    mutationFn: ({ id, lineId, version }) =>
      removeOrderLine(id, lineId, version),
    retry: false,
    onSuccess: (order) => {
      afterOrderChange(queryClient, order);
    },
    onError: (error) => {
      note401(error, queryClient);
    },
  });
}

/**
 * POST /api/orders/{id}/confirm, /cancel or /ship with `If-Match`.
 * Confirming and cancelling change the stock, so both invalidate the
 * product catalog; shipping does not.
 */
export function useOrderTransition(): UseMutationResult<
  Order,
  ApiRequestError,
  { id: number; action: OrderTransitionAction; version: number }
> {
  const queryClient = useQueryClient();

  return useMutation<
    Order,
    ApiRequestError,
    { id: number; action: OrderTransitionAction; version: number }
  >({
    mutationFn: ({ id, action, version }) =>
      transitionOrder(id, action, version),
    retry: false,
    onSuccess: (order, { action }) => {
      afterOrderChange(queryClient, order, {
        products: action === "confirm" || action === "cancel",
      });
    },
    onError: (error) => {
      note401(error, queryClient);
    },
  });
}
