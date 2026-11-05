/**
 * Types of the customers module. The fields and the status values come from
 * docs/SPEC.md section 4.
 */

export type CustomerStatus = "active" | "inactive";

/**
 * A customer as the API returns it. `phone`, `tax_id` and `address` are
 * `null` when empty; the timestamps are ISO 8601 in UTC with a trailing
 * `Z`; `version` starts at 1 and increases on every change.
 */
export type Customer = {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  tax_id: string | null;
  address: string | null;
  status: CustomerStatus;
  version: number;
  created_at: string;
  updated_at: string;
};

/** One page of the list: `{items, page, page_size, total}` of the spec. */
export type CustomerList = {
  items: Customer[];
  page: number;
  page_size: number;
  total: number;
};

const STATUS_LABELS: Record<CustomerStatus, string> = {
  active: "Activo",
  inactive: "Inactivo",
};

/** Spanish label of a status, as shown in the list and the detail page. */
export function statusLabel(status: CustomerStatus): string {
  return STATUS_LABELS[status];
}
