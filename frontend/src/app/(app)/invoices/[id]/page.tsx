"use client";

import { Alert, Button, Input, Link, Select } from "@/components/ui";
import { useMe } from "@/features/auth/hooks";
import { newIdempotencyKey } from "@/features/invoices/idempotency";
import { useInvoice, useRegisterPayment } from "@/features/invoices/hooks";
import { parseInvoiceIdParam } from "@/features/invoices/params";
import { canManageInvoices } from "@/features/invoices/permissions";
import type { ApiFieldError } from "@/lib/api";
import { ApiRequestError, INTERNAL_ERROR_DETAIL } from "@/lib/api";
import type { PaymentBody } from "@/features/invoices/api";
import { formatDateTime, formatMoney } from "@/lib/format";
import type { Invoice, InvoiceLine, Payment } from "@/features/invoices/types";
import {
  invoiceStatusLabel,
  paymentMethodLabel,
  paymentReasonLabel,
  paymentStatusLabel,
} from "@/features/invoices/types";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

const REQUIRED_MESSAGE = "Este campo es obligatorio.";

/** The classes of a ledger header cell and a ledger body cell. */
const TABLE_HEAD_CLASSES = [
  "border-b-2 border-ink px-[10px] py-[9px] text-left",
  "text-xs font-medium uppercase tracking-[0.07em] text-muted",
].join(" ");

const TABLE_CELL_CLASSES =
  "border-b border-line px-[10px] py-[9px] text-ink tabular-nums";

const STATE_BADGE_CLASSES = "inline-flex rounded-sm px-2 py-0.5 text-xs font-semibold";

/** The badge colors of the theme: only a paid invoice is positive. */
function invoiceBadgeClasses(status: Invoice["status"]): string {
  const positive = status === "paid";
  return [
    STATE_BADGE_CLASSES,
    positive ? "bg-ok-bg text-accent" : "bg-off-bg text-muted",
  ].join(" ");
}

/** One labeled value of the info card. */
function DetailRow({ label, children }: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid items-baseline gap-1 sm:grid-cols-[160px_minmax(0,1fr)] sm:gap-4">
      <dt className="text-[13px] font-medium text-muted">{label}</dt>
      {children}
    </div>
  );
}

/** One row of the payment history table. */
function PaymentRow({ payment }: { payment: Payment }) {
  const detail =
    payment.status !== "approved" && payment.reason !== null
      ? paymentReasonLabel(payment.reason)
      : payment.method === "card"
        ? `Tarjeta ···· ${payment.card_last4 ?? "—"}`
        : payment.method === "transfer"
          ? payment.reference ?? "—"
          : "—";
  return (
    <tr
      data-testid={`invoices-detail-payment-row-${payment.id}`}
      className="ledger-row"
    >
      <td
        data-testid={`invoices-detail-payment-method-cell-${payment.id}`}
        className={TABLE_CELL_CLASSES}
      >
        {paymentMethodLabel(payment.method)}
      </td>
      <td
        data-testid={`invoices-detail-payment-state-cell-${payment.id}`}
        className={`${TABLE_CELL_CLASSES} whitespace-nowrap`}
      >
        <span
          className={[
            STATE_BADGE_CLASSES,
            payment.status === "approved"
              ? "bg-ok-bg text-accent"
              : "bg-off-bg text-muted",
          ].join(" ")}
        >
          {paymentStatusLabel(payment.status)}
        </span>
      </td>
      <td
        data-testid={`invoices-detail-payment-amount-cell-${payment.id}`}
        className={TABLE_CELL_CLASSES}
      >
        {formatMoney(payment.amount)}
      </td>
      <td
        data-testid={`invoices-detail-payment-detail-cell-${payment.id}`}
        className={TABLE_CELL_CLASSES}
      >
        {detail}
      </td>
      <td className={`${TABLE_CELL_CLASSES} whitespace-nowrap`}>
        {formatDateTime(payment.created_at)}
      </td>
    </tr>
  );
}

const PAYMENT_FIELDS: readonly string[] = [
  "method",
  "amount",
  "card.number",
  "card.expiry",
  "card.cvc",
  "reference",
];

/**
 * The register-payment form of an issued invoice. The form owns ONE
 * idempotency key: it keeps the same key after a network error (no
 * answer arrived, so a retry is safe and replays or continues), takes a
 * new key after any HTTP answer (a retry after a decline or a failure is
 * a new attempt, per the spec) and whenever the user changes a field.
 */
function RegisterPaymentForm({ invoice, onApproved, refetchInvoice }: {
  invoice: Invoice;
  /** The approved payment moved the invoice to paid on success. */
  onApproved: () => void;
  /** Refetches after any failed submit, as the brief asks. */
  refetchInvoice: () => void;
}) {
  const payment = useRegisterPayment();

  const [method, setMethod] = useState<"card" | "transfer" | "cash">("card");
  const [amount, setAmount] = useState(invoice.total);
  const [cardNumber, setCardNumber] = useState("");
  const [cardExpiry, setCardExpiry] = useState("");
  const [cardCvc, setCardCvc] = useState("");
  const [reference, setReference] = useState("");

  const [methodError, setMethodError] = useState<string | null>(null);
  const [amountError, setAmountError] = useState<string | null>(null);
  const [cardNumberError, setCardNumberError] = useState<string | null>(null);
  const [cardExpiryError, setCardExpiryError] = useState<string | null>(null);
  const [cardCvcError, setCardCvcError] = useState<string | null>(null);
  const [referenceError, setReferenceError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  // One increment per failed submit; the focus effect below depends on it.
  const [failureCount, setFailureCount] = useState(0);
  const formAlertRef = useRef<HTMLParagraphElement>(null);

  const [idempotencyKey, setIdempotencyKey] = useState(() => newIdempotencyKey());
  const submittingRef = useRef(false);

  /** Each field change takes a new key: the protected body changed. */
  function changeField(setter: (value: string) => void) {
    return (value: string) => {
      setter(value);
      setIdempotencyKey(newIdempotencyKey());
    };
  }

  // Focus after a failure: the form-level alert when it is shown,
  // otherwise the first field with an error.
  useEffect(() => {
    if (!formError && !methodError && !amountError && !cardNumberError
      && !cardExpiryError && !cardCvcError && !referenceError) {
      return;
    }
    if (formError) {
      formAlertRef.current?.focus();
    } else if (methodError) {
      document.getElementById("payments-register-method")?.focus();
    } else if (amountError) {
      document.getElementById("payments-register-amount")?.focus();
    } else if (cardNumberError) {
      document.getElementById("payments-register-cardnumber")?.focus();
    } else if (cardExpiryError) {
      document.getElementById("payments-register-cardexpiry")?.focus();
    } else if (cardCvcError) {
      document.getElementById("payments-register-cardcvc")?.focus();
    } else if (referenceError) {
      document.getElementById("payments-register-reference")?.focus();
    }
  }, [
    failureCount,
    formError,
    methodError,
    amountError,
    cardNumberError,
    cardExpiryError,
    cardCvcError,
    referenceError,
  ]);

  function fieldErrorsOf(error: unknown): ApiFieldError[] {
    if (error instanceof ApiRequestError) {
      return error.problem.errors ?? [];
    }
    return [];
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submittingRef.current || payment.isPending) {
      return;
    }

    // Client side, only the required check of an empty field; every other
    // rule (Luhn, expiry format, the amount shape) is the server's, and
    // the card number travels as typed, spaces and hyphens included.
    const nextErrors: Record<string, string | null> = {
      methodError: null,
      amountError: amount.trim() === "" ? REQUIRED_MESSAGE : null,
      cardNumberError:
        (method === "card" && cardNumber.trim() === "") ? REQUIRED_MESSAGE : null,
      cardExpiryError:
        (method === "card" && cardExpiry.trim() === "") ? REQUIRED_MESSAGE : null,
      cardCvcError:
        (method === "card" && cardCvc.trim() === "") ? REQUIRED_MESSAGE : null,
      referenceError:
        (method === "transfer" && reference.trim() === "")
          ? REQUIRED_MESSAGE
          : null,
    };
    if (Object.values(nextErrors).some((message) => message !== null)) {
      setFailureCount((count) => count + 1);
      setMethodError(nextErrors.methodError ?? null);
      setAmountError(nextErrors.amountError ?? null);
      setCardNumberError(nextErrors.cardNumberError ?? null);
      setCardExpiryError(nextErrors.cardExpiryError ?? null);
      setCardCvcError(nextErrors.cardCvcError ?? null);
      setReferenceError(nextErrors.referenceError ?? null);
      setFormError(null);
      return;
    }

    // Each submit clears the errors of the previous one.
    setMethodError(null);
    setAmountError(null);
    setCardNumberError(null);
    setCardExpiryError(null);
    setCardCvcError(null);
    setReferenceError(null);
    setFormError(null);

    // The body carries only the fields of the method.
    const requestBody: PaymentBody = method === "card"
      ? {
          method: "card",
          amount: amount.trim(),
          card: { number: cardNumber, expiry: cardExpiry, cvc: cardCvc },
        }
      : method === "transfer"
        ? {
            method: "transfer",
            amount: amount.trim(),
            reference: reference.trim(),
          }
        : { method: "cash", amount: amount.trim() };

    submittingRef.current = true;
    try {
      await payment.mutateAsync({
        invoiceId: invoice.id,
        body: requestBody,
        idempotencyKey,
        version: invoice.version,
      });
      // The answer arrived: the attempt consumed the key, and the next
      // attempt is a new one.
      onApproved();
      setIdempotencyKey(newIdempotencyKey());
      // Privacy: the card fields never outlive a paid payment.
      setCardNumber("");
      setCardExpiry("");
      setCardCvc("");
    } catch (error) {
      setFailureCount((count) => count + 1);
      // What the key knows about the attempt (the review of 020): a key
      // is only retired when the answer tells the user the attempt is
      // over.
      //  - No answer arrived (the network has none: status 0 under
      //    `apiFetch`), or the answer is 429 `RATE_LIMITED` (nothing
      //    happened): a retry is safe and replays or continues.
      //  - The answer is 500 or above, except `PAYMENT_GATEWAY_UNAVAILABLE`:
      //    a 500 `INTERNAL_ERROR`, a 502 or a 504 from the platform (a
      //    function that timed out while the gateway was approving) says
      //    nothing about whether the payment was recorded; a new key would
      //    make the retry a brand new payment instead of a replay.
      //  - Every other answer (201, the codes of section 7 like 402, 409,
      //    422 and 403, and the 503 `PAYMENT_GATEWAY_UNAVAILABLE`) tells
      //    the outcome: the next attempt is a new one.
      const status = error instanceof ApiRequestError
        ? error.problem.status
        : 0;
      const code = error instanceof ApiRequestError
        ? error.problem.code
        : undefined;
      const outcomeUnknown =
        status === 0
        || status === 429
        || (status >= 500 && code !== "PAYMENT_GATEWAY_UNAVAILABLE")
        || !(error instanceof ApiRequestError);
      if (!outcomeUnknown) {
        setIdempotencyKey(newIdempotencyKey());
      }
      if (error instanceof ApiRequestError && status !== 0) {
        // Any field of `errors[]` maps to its own field; when none of the
        // entries is a known field, the detail goes to the form-level
        // alert.
        const entries = fieldErrorsOf(error).filter((entry) =>
          PAYMENT_FIELDS.includes(entry.field),
        );
        if (entries.length > 0) {
          for (const mapped of entries) {
            if (mapped.field === "method") {
              setMethodError(mapped.message);
            } else if (mapped.field === "amount") {
              setAmountError(mapped.message);
            } else if (mapped.field === "card.number") {
              setCardNumberError(mapped.message);
            } else if (mapped.field === "card.expiry") {
              setCardExpiryError(mapped.message);
            } else if (mapped.field === "card.cvc") {
              setCardCvcError(mapped.message);
            } else if (mapped.field === "reference") {
              setReferenceError(mapped.message);
            }
          }
        } else {
          setFormError(error.problem.detail);
        }
        // VERSION_CONFLICT, INVOICE_NOT_PAYABLE, the amount mismatch, the
        // declined and the failed answers: the invoice is refetched so a
        // corrected retry carries a fresh version (and for a 402 or a
        // 503, the history shows the attempt).
        refetchInvoice();
      } else {
        // No answer arrived: the key stays, a retry is safe and replays
        // or continues.
        setFormError(INTERNAL_ERROR_DETAIL);
      }
    } finally {
      submittingRef.current = false;
    }
  }

  return (
    <section className="mt-6">
      <h2
        data-testid="payments-register-heading"
        className="text-lg font-semibold"
      >
        Registrar un pago
      </h2>

      {formError ? (
        <div className="mt-3">
          <Alert
            ref={formAlertRef}
            testId="payments-register-alert"
            tabIndex={-1}
          >
            {formError}
          </Alert>
        </div>
      ) : null}

      {/*
       * The form of the payment, only for an issued invoice a user who
       * can manage invoices: the select has no placeholder, and the
       * fields of the other methods are not rendered when one is chosen.
       */}
      <form
        noValidate
        onSubmit={handleSubmit}
        data-testid="payments-register-form"
        className="mt-3 flex flex-col gap-4"
      >
        <div className="flex flex-wrap items-end gap-3">
          <Select
            id="payments-register-method"
            testId="payments-register-method-select"
            label="Método"
            value={method}
            onChange={(event) => {
              // A switch of method clears the field errors of the
              // previous one; the fields of the other method and their
              // values are never sent. A field change takes a new key.
              setMethod(event.target.value as "card" | "transfer" | "cash");
              setCardNumberError(null);
              setCardExpiryError(null);
              setCardCvcError(null);
              setReferenceError(null);
              setIdempotencyKey(newIdempotencyKey());
            }}
            error={methodError ?? undefined}
          >
            <option value="card">Tarjeta</option>
            <option value="transfer">Transferencia</option>
            <option value="cash">Efectivo</option>
          </Select>
          <Input
            id="payments-register-amount"
            testId="payments-register-amount-input"
            label="Monto"
            value={amount}
            onChange={(event) => changeField(setAmount)(event.target.value)}
            error={amountError ?? undefined}
          />
        </div>

        {method === "card" ? (
          <div className="flex flex-wrap items-end gap-3">
            <Input
              id="payments-register-cardnumber"
              testId="payments-register-cardnumber-input"
              label="Número de tarjeta"
              autoComplete="off"
              value={cardNumber}
              onChange={(event) => changeField(setCardNumber)(event.target.value)}
              error={cardNumberError ?? undefined}
            />
            <Input
              id="payments-register-cardexpiry"
              testId="payments-register-cardexpiry-input"
              label="Vencimiento (MM/AA)"
              autoComplete="off"
              value={cardExpiry}
              onChange={(event) => changeField(setCardExpiry)(event.target.value)}
              error={cardExpiryError ?? undefined}
            />
            <Input
              id="payments-register-cardcvc"
              testId="payments-register-cardcvc-input"
              label="CVC"
              autoComplete="off"
              value={cardCvc}
              onChange={(event) => changeField(setCardCvc)(event.target.value)}
              error={cardCvcError ?? undefined}
            />
          </div>
        ) : method === "transfer" ? (
          <Input
            id="payments-register-reference"
            testId="payments-register-reference-input"
            label="Referencia"
            value={reference}
            onChange={(event) => changeField(setReference)(event.target.value)}
            error={referenceError ?? undefined}
          />
        ) : null}

        <div>
          <Button
            testId="payments-register-submit-button"
            type="submit"
            loading={payment.isPending}
            disabled={payment.isPending}
          >
            {payment.isPending ? "Pagando…" : "Pagar"}
          </Button>
        </div>
      </form>
    </section>
  );
}

/** The detail of one invoice, with its payment history. */
function Detail({ id }: { id: number }) {
  const me = useMe();
  const invoiceQuery = useInvoice(id);

  // The success message of the payment lives in the detail: once the
  // invoice is paid the form unmounts in the same render that shows it.
  const [paymentApproved, setPaymentApproved] = useState(false);

  if (invoiceQuery.isPending) {
    return (
      <p
        role="status"
        data-testid="invoices-detail-loading-status"
        aria-busy="true"
        className="text-muted"
      >
        Cargando…
      </p>
    );
  }

  if (invoiceQuery.isError) {
    const problem = invoiceQuery.error instanceof ApiRequestError
      ? invoiceQuery.error.problem
      : { status: 0, detail: INTERNAL_ERROR_DETAIL };
    const is404 = problem.status === 404;

    return (
      <div>
        <Alert testId="invoices-detail-error-alert">
          {problem.detail}
        </Alert>
        <div className="mt-3">
          {is404 ? null : (
            <Button
              testId="invoices-detail-retry-button"
              onClick={() => void invoiceQuery.refetch()}
            >
              Reintentar
            </Button>
          )}
        </div>
        <div className="mt-3">
          <Link href="/invoices" testId="invoices-detail-back-link">
            Volver a facturas
          </Link>
        </div>
      </div>
    );
  }

  const invoice = invoiceQuery.data;
  const lines = invoice.lines;
  const canManage = me.data ? canManageInvoices(me.data.role) : false;

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 data-testid="invoices-detail-heading">{invoice.number}</h1>
        <span
          data-testid="invoices-detail-state-status"
          className={invoiceBadgeClasses(invoice.status)}
        >
          {invoiceStatusLabel(invoice.status)}
        </span>
      </div>

      {paymentApproved ? (
        <p
          role="status"
          data-testid="payments-register-success-status"
          className="mt-3 text-[13px] font-medium text-accent"
        >
          Pago aprobado.
        </p>
      ) : null}

      {invoice.status === "paid" || invoice.status === "void" ? (
        <p
          data-testid="invoices-detail-closed-text"
          className="mt-3 text-[13px] text-muted"
        >
          {invoice.status === "paid"
            ? "Esta factura está pagada."
            : "Esta factura fue anulada."}
        </p>
      ) : null}

      {/* The frozen facts of the invoice in a surface card. */}
      <div className="mt-6 rounded-lg border border-line bg-surface p-5">
        <dl className="flex flex-col gap-3">
          <DetailRow label="Pedido">
            <dd>
              <Link
                href={`/orders/${invoice.order_id}`}
                testId="invoices-detail-order-link"
              >
                {invoice.order_number}
              </Link>
            </dd>
          </DetailRow>
          <DetailRow label="Cliente al emitir">
            <dd
              data-testid="invoices-detail-customer-text"
              className="break-words"
            >
              {invoice.customer.name}
            </dd>
          </DetailRow>
          <DetailRow label="ID fiscal">
            <dd
              data-testid="invoices-detail-taxid-text"
              className="break-words tabular-nums"
            >
              {invoice.customer.tax_id ?? <span className="text-muted">—</span>}
            </dd>
          </DetailRow>
          <DetailRow label="Dirección">
            <dd
              data-testid="invoices-detail-address-text"
              className="break-words"
            >
              {invoice.customer.address ?? <span className="text-muted">—</span>}
            </dd>
          </DetailRow>
          <DetailRow label="Creada">
            <dd
              data-testid="invoices-detail-created-text"
              className="break-words tabular-nums"
            >
              {formatDateTime(invoice.created_at)}
            </dd>
          </DetailRow>
        </dl>
      </div>

      {/* The snapshot of the lines with the frozen totals under them. */}
      <div className="mt-6 rounded-lg border border-line bg-surface p-5">
        <h2
          data-testid="invoices-detail-lines-heading"
          className="text-lg font-semibold"
        >
          Líneas
        </h2>
        <div className="mt-3 overflow-x-auto p-1.5">
          <table
            data-testid="invoices-detail-lines-table"
            className="min-w-[36rem] w-full"
          >
            <thead>
              <tr>
                <th scope="col" className={TABLE_HEAD_CLASSES}>Producto</th>
                <th scope="col" className={TABLE_HEAD_CLASSES}>Cantidad</th>
                <th scope="col" className={TABLE_HEAD_CLASSES}>Precio unitario</th>
                <th scope="col" className={TABLE_HEAD_CLASSES}>Subtotal</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line: InvoiceLine) => (
                <tr
                  key={line.id}
                  data-testid={`invoices-detail-line-row-${line.id}`}
                  className="ledger-row"
                >
                  <td
                    data-testid={`invoices-detail-line-product-cell-${line.id}`}
                    className={TABLE_CELL_CLASSES}
                  >
                    {line.name} ({line.sku})
                  </td>
                  <td
                    data-testid={`invoices-detail-line-quantity-cell-${line.id}`}
                    className={TABLE_CELL_CLASSES}
                  >
                    {line.quantity}
                  </td>
                  <td
                    data-testid={`invoices-detail-line-price-cell-${line.id}`}
                    className={TABLE_CELL_CLASSES}
                  >
                    {formatMoney(line.unit_price)}
                  </td>
                  <td
                    data-testid={`invoices-detail-line-total-cell-${line.id}`}
                    className={TABLE_CELL_CLASSES}
                  >
                    {formatMoney(line.line_total)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/*
         * The totals of the invoice: the ledger with the double rule
         * above the total.
         */}
        <div className="mt-4 flex flex-col items-end gap-1 text-right">
          <p className="flex gap-4 tabular-nums">
            <span className="font-medium text-muted">Subtotal</span>
            <span data-testid="invoices-detail-subtotal-text">
              {formatMoney(invoice.subtotal)}
            </span>
          </p>
          <p className="flex gap-4 tabular-nums">
            <span
              data-testid="invoices-detail-taxrate-text"
              className="font-medium text-muted"
            >
              Impuesto ({invoice.tax_rate} %)
            </span>
            <span data-testid="invoices-detail-tax-text">
              {formatMoney(invoice.tax)}
            </span>
          </p>
          <div className="flex gap-4 border-t-4 border-double border-ink pt-2 tabular-nums">
            <span className="font-semibold">Total</span>
            <span
              data-testid="invoices-detail-total-text"
              className="font-semibold"
            >
              {formatMoney(invoice.total)}
            </span>
          </div>
        </div>
      </div>

      {/* The payment history of the invoice. */}
      <div className="mt-6 rounded-lg border border-line bg-surface p-5">
        <h2
          data-testid="invoices-detail-payments-heading"
          className="text-lg font-semibold"
        >
          Pagos
        </h2>
        {invoice.payments.length === 0 ? (
          <p
            data-testid="invoices-detail-nopayments-text"
            className="mt-3 text-muted"
          >
            Aún no hay pagos.
          </p>
        ) : (
          <div className="mt-3 overflow-x-auto p-1.5">
            <table
              data-testid="invoices-detail-payments-table"
              className="min-w-[40rem] w-full"
            >
              <thead>
                <tr>
                  <th scope="col" className={TABLE_HEAD_CLASSES}>Método</th>
                  <th scope="col" className={TABLE_HEAD_CLASSES}>Estado</th>
                  <th scope="col" className={TABLE_HEAD_CLASSES}>Monto</th>
                  <th scope="col" className={TABLE_HEAD_CLASSES}>Detalle</th>
                  <th scope="col" className={TABLE_HEAD_CLASSES}>Fecha</th>
                </tr>
              </thead>
              <tbody>
                {invoice.payments.map((payment) => (
                  <PaymentRow key={payment.id} payment={payment} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* The payment form: only for an issued invoice and only for the
          roles that manage invoices; the closed note already explains a
          paid or void invoice. */}
      {canManage && invoice.status === "issued" ? (
        <RegisterPaymentForm
          invoice={invoice}
          onApproved={() => setPaymentApproved(true)}
          refetchInvoice={() => void invoiceQuery.refetch()}
        />
      ) : null}

      <div className="mt-6">
        <Link href="/invoices" testId="invoices-detail-back-link">
          Volver a facturas
        </Link>
      </div>
    </div>
  );
}

export default function InvoiceDetailPage() {
  const id = parseInvoiceIdParam(useParams().id);

  if (id === null) {
    // Not a valid id: show the not-found alert and the back link without
    // calling the API.
    return (
      <div>
        <Alert testId="invoices-detail-error-alert">
          No se encontró el recurso solicitado.
        </Alert>
        <div className="mt-3">
          <Link href="/invoices" testId="invoices-detail-back-link">
            Volver a facturas
          </Link>
        </div>
      </div>
    );
  }

  return <Detail id={id} />;
}
