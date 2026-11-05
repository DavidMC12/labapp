/**
 * Types of the orders module. The shapes are the "Orders API" subsection
 * of docs/SPEC.md: money as strings with exactly 2 decimals, the tax rate
 * as a string, ids and quantities as integers and `invoice_id` as
 * `number | null`. A `draft` carries the current tax rate as a preview;
 * every other status (including `cancelled`) has the frozen rate and
 * totals.
 */

export type OrderStatus =
  | "draft"
  | "confirmed"
  | "paid"
  | "shipped"
  | "cancelled";

/** The customer of an order as the API returns it inside `Order`. */
export type OrderCustomer = {
  id: number;
  name: string;
  status: "active" | "inactive";
};

/** One line: `unit_price` and `line_total` are strings of 2 decimals. */
export type OrderLine = {
  id: number;
  product_id: number;
  sku: string;
  name: string;
  quantity: number;
  unit_price: string;
  line_total: string;
};

/** One order as `GET /api/orders/{id}` answers it. */
export type Order = {
  id: number;
  number: string;
  status: OrderStatus;
  customer: OrderCustomer;
  lines: OrderLine[];
  subtotal: string;
  tax_rate: string;
  tax: string;
  total: string;
  invoice_id: number | null;
  version: number;
  created_at: string;
  updated_at: string;
};

/** One row of the orders list (`GET /api/orders`). */
export type OrderSummary = {
  id: number;
  number: string;
  status: OrderStatus;
  customer_id: number;
  customer_name: string;
  line_count: number;
  total: string;
  version: number;
  created_at: string;
  updated_at: string;
};

/** One page of the list: `{items, page, page_size, total}` of the spec. */
export type OrderList = {
  items: OrderSummary[];
  page: number;
  page_size: number;
  total: number;
};

/** A read-only product of the catalog (`GET /api/products`). */
export type Product = {
  id: number;
  sku: string;
  name: string;
  price: string;
  stock: number;
};

/**
 * One short line of `shortages[]` in a 409 `INSUFFICIENT_STOCK`, ordered
 * by product id (docs/SPEC.md section 5).
 */
export type Shortage = {
  product_id: number;
  sku: string;
  name: string;
  available: number;
  requested: number;
};

const STATUS_LABELS: Record<OrderStatus, string> = {
  draft: "Borrador",
  confirmed: "Confirmado",
  paid: "Pagado",
  shipped: "Enviado",
  cancelled: "Cancelado",
};

/** Spanish label of a status, as shown in the list and the detail page. */
export function orderStatusLabel(status: OrderStatus): string {
  return STATUS_LABELS[status];
}
