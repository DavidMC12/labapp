/**
 * Types of the invoices module. The shapes are the "Invoices and payments
 * API" subsection of docs/SPEC.md: money as strings with exactly 2
 * decimals, ids and quantities as integers, and the snapshot fields
 * (`tax_id`, `address`) as `string | null`.
 */

export type InvoiceStatus = "issued" | "paid" | "void";

/** The customer snapshot taken when the invoice was issued. */
export type InvoiceCustomer = {
  id: number;
  name: string;
  tax_id: string | null;
  address: string | null;
};

/** One line snapshot: `unit_price` and `line_total` are 2-decimal strings. */
export type InvoiceLine = {
  id: number;
  product_id: number;
  sku: string;
  name: string;
  quantity: number;
  unit_price: string;
  line_total: string;
};

/** One attempt of the payment history, ordered by `id` in the invoice. */
export type PaymentMethod = "card" | "transfer" | "cash";

export type PaymentStatus = "approved" | "declined" | "failed";

export type PaymentReason = "CARD_DECLINED" | "GATEWAY_UNAVAILABLE";

export type Payment = {
  id: number;
  method: PaymentMethod;
  status: PaymentStatus;
  amount: string;
  /** Only for a transfer. */
  reference: string | null;
  /** Only for a card: the only part ever stored or returned. */
  card_last4: string | null;
  /** Only for a declined or a failed payment. */
  reason: PaymentReason | null;
  created_at: string;
};

/** One invoice as `GET /api/invoices/{id}` answers it. */
export type Invoice = {
  id: number;
  number: string;
  status: InvoiceStatus;
  order_id: number;
  order_number: string;
  customer: InvoiceCustomer;
  lines: InvoiceLine[];
  subtotal: string;
  tax_rate: string;
  tax: string;
  total: string;
  payments: Payment[];
  version: number;
  created_at: string;
  updated_at: string;
};

/** One row of the invoices list (`GET /api/invoices`). */
export type InvoiceSummary = {
  id: number;
  number: string;
  status: InvoiceStatus;
  order_id: number;
  order_number: string;
  customer_name: string;
  total: string;
  version: number;
  created_at: string;
  updated_at: string;
};

/** One page of the list: `{items, page, page_size, total}` of the spec. */
export type InvoiceList = {
  items: InvoiceSummary[];
  page: number;
  page_size: number;
  total: number;
};

/** The 201 answer of a payment: the payment and the invoice after it. */
export type PaymentResult = {
  payment: Payment;
  invoice: Invoice;
};

const INVOICE_STATUS_LABELS: Record<InvoiceStatus, string> = {
  issued: "Emitida",
  paid: "Pagada",
  void: "Anulada",
};

const PAYMENT_STATUS_LABELS: Record<PaymentStatus, string> = {
  approved: "Aprobado",
  declined: "Rechazado",
  failed: "Fallido",
};

const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  card: "Tarjeta",
  transfer: "Transferencia",
  cash: "Efectivo",
};

const REASON_LABELS: Record<PaymentReason, string> = {
  CARD_DECLINED: "Tarjeta rechazada",
  GATEWAY_UNAVAILABLE: "Pasarela no disponible",
};

/** Spanish label of an invoice status. */
export function invoiceStatusLabel(status: InvoiceStatus): string {
  return INVOICE_STATUS_LABELS[status];
}

/** Spanish label of a payment status. */
export function paymentStatusLabel(status: PaymentStatus): string {
  return PAYMENT_STATUS_LABELS[status];
}

/** Spanish label of a payment method. */
export function paymentMethodLabel(method: PaymentMethod): string {
  return PAYMENT_METHOD_LABELS[method];
}

/** Spanish label of a gateway reason. */
export function paymentReasonLabel(reason: PaymentReason): string {
  return REASON_LABELS[reason];
}
