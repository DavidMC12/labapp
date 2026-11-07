/**
 * The counters of the home "Resumen" (task 026). Each counter is the
 * `total` of a list request with its `status` filter, so the summary
 * always shows live counts; nothing is hard coded. The requests reuse the
 * list hooks and query keys of the three modules, so a visited list and
 * the summary share one cache entry, and a failing request breaks only
 * its own card.
 */

import { useCustomers } from "@/features/customers/hooks";
import { statusLabel } from "@/features/customers/types";
import { useInvoices } from "@/features/invoices/hooks";
import { invoiceStatusLabel } from "@/features/invoices/types";
import { useOrders } from "@/features/orders/hooks";
import { orderStatusLabel } from "@/features/orders/types";
import type {
  CustomerList,
} from "@/features/customers/types";
import type {
  InvoiceList,
} from "@/features/invoices/types";
import type { ApiRequestError } from "@/lib/api";
import type { TestId } from "@/lib/testid";
import type {
  OrderList,
} from "@/features/orders/types";
import type {
  UseQueryResult,
} from "@tanstack/react-query";

/** The list result behind one counter, with its own loading and error state. */
export type SummaryList =
  UseQueryResult<CustomerList | OrderList | InvoiceList, ApiRequestError>;

/** One counter of the summary: a status, its label, its link and its request. */
export type SummaryCounter = {
  /** The `status` filter value the counter shows (for example `confirmed`). */
  status: string;
  /** The label of the status, from the module's label helper. */
  label: string;
  /** The filtered list the counter links to (what the list screen reads). */
  href: string;
  /** The ids of the id contract the counter needs (typed literals). */
  linkTestId: TestId;
  countTestId: TestId;
  loadingTestId: TestId;
  /** The list request that carries the `total` and its states. */
  list: SummaryList;
};

export type SummaryGroupKey = "customers" | "orders" | "invoices";

/** One section of the summary: its heading, its counters and its retry. */
export type SummaryGroup = {
  key: SummaryGroupKey;
  headingTestId: TestId;
  retryTestId: TestId;
  counters: SummaryCounter[];
};

export type Summary = {
  groups: SummaryGroup[];
};

const CUSTOMER_STATUS_COUNTERS = [
  { status: "active", label: statusLabel("active") },
  { status: "inactive", label: statusLabel("inactive") },
] as const;

const ORDER_STATUS_COUNTERS = [
  { status: "draft", label: orderStatusLabel("draft") },
  { status: "confirmed", label: orderStatusLabel("confirmed") },
  { status: "paid", label: orderStatusLabel("paid") },
  { status: "shipped", label: orderStatusLabel("shipped") },
  { status: "cancelled", label: orderStatusLabel("cancelled") },
] as const;

const INVOICE_STATUS_COUNTERS = [
  { status: "issued", label: invoiceStatusLabel("issued") },
  { status: "paid", label: invoiceStatusLabel("paid") },
  { status: "void", label: invoiceStatusLabel("void") },
] as const;

type CounterDef<S extends string> = {
  status: S;
  label: string;
  href: string;
  linkTestId: TestId;
  countTestId: TestId;
  loadingTestId: TestId;
};

/** The ids follow `<group>-<name>-<kind>` under the `home` module. */
function counterDef<S extends string>(
  group: SummaryGroupKey,
  def: { status: S; label: string },
): CounterDef<S> {
  return {
    ...def,
    href: `/${group}?status=${def.status}`,
    linkTestId: `home-${group}-${def.status}-link` as TestId,
    countTestId: `home-${group}-${def.status}-count-text` as TestId,
    loadingTestId:
      `home-${group}-${def.status}-loading-status` as TestId,
  };
}

const CUSTOMER_COUNTERS: CounterDef<(typeof CUSTOMER_STATUS_COUNTERS)[number]["status"]>[] = [];
CUSTOMER_STATUS_COUNTERS.forEach((counter) => {
  CUSTOMER_COUNTERS.push(counterDef("customers", counter));
});

const ORDER_COUNTERS: CounterDef<(typeof ORDER_STATUS_COUNTERS)[number]["status"]>[] = [];
ORDER_STATUS_COUNTERS.forEach((counter) => {
  ORDER_COUNTERS.push(counterDef("orders", counter));
});

const INVOICE_COUNTERS: CounterDef<(typeof INVOICE_STATUS_COUNTERS)[number]["status"]>[] = [];
INVOICE_STATUS_COUNTERS.forEach((counter) => {
  INVOICE_COUNTERS.push(counterDef("invoices", counter));
});

/**
 * One counter per status, each list request `GET ...?page=1&status=...`
 * through the list hooks of its module (`retry: false`, and a 401 writes
 * `null` into the me key so the shell redirects).
 */
export function useSummary(): Summary {
  const customersActive = useCustomers({ page: 1, status: "active" });
  const customersInactive = useCustomers({ page: 1, status: "inactive" });

  const ordersDraft = useOrders({ page: 1, status: "draft" });
  const ordersConfirmed = useOrders({ page: 1, status: "confirmed" });
  const ordersPaid = useOrders({ page: 1, status: "paid" });
  const ordersShipped = useOrders({ page: 1, status: "shipped" });
  const ordersCancelled = useOrders({ page: 1, status: "cancelled" });

  const invoicesIssued = useInvoices({ page: 1, status: "issued" });
  const invoicesPaid = useInvoices({ page: 1, status: "paid" });
  const invoicesVoid = useInvoices({ page: 1, status: "void" });

  const customersGroup: SummaryGroup = {
    key: "customers",
    headingTestId: "home-customers-heading",
    retryTestId: "home-customers-retry-button",
    counters: [
      { ...CUSTOMER_COUNTERS[0], list: customersActive },
      { ...CUSTOMER_COUNTERS[1], list: customersInactive },
    ],
  };

  const ordersGroup: SummaryGroup = {
    key: "orders",
    headingTestId: "home-orders-heading",
    retryTestId: "home-orders-retry-button",
    counters: [
      { ...ORDER_COUNTERS[0], list: ordersDraft },
      { ...ORDER_COUNTERS[1], list: ordersConfirmed },
      { ...ORDER_COUNTERS[2], list: ordersPaid },
      { ...ORDER_COUNTERS[3], list: ordersShipped },
      { ...ORDER_COUNTERS[4], list: ordersCancelled },
    ],
  };

  const invoicesGroup: SummaryGroup = {
    key: "invoices",
    headingTestId: "home-invoices-heading",
    retryTestId: "home-invoices-retry-button",
    counters: [
      { ...INVOICE_COUNTERS[0], list: invoicesIssued },
      { ...INVOICE_COUNTERS[1], list: invoicesPaid },
      { ...INVOICE_COUNTERS[2], list: invoicesVoid },
    ],
  };

  return { groups: [customersGroup, ordersGroup, invoicesGroup] };
}
