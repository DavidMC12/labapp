"use client";

import {
  Alert,
  Button,
  ConfirmDialog,
  Input,
  Link,
  Select,
} from "@/components/ui";
import { useMe } from "@/features/auth/hooks";
import { canManageInvoices } from "@/features/invoices/permissions";
import { useIssueInvoice } from "@/features/invoices/hooks";
import {
  useAddLine,
  useOrder,
  useOrderTransition,
  useProducts,
  useRemoveLine,
  useSetLineQuantity,
  useSetOrderCustomer,
} from "@/features/orders/hooks";
import { parseOrderIdParam } from "@/features/orders/params";
import {
  canEditOrders,
  canTransitionOrders,
} from "@/features/orders/permissions";
import { useCustomers } from "@/features/customers/hooks";
import type { CustomerList } from "@/features/customers/types";
import { ApiRequestError, INTERNAL_ERROR_DETAIL } from "@/lib/api";
import { useDocumentTitle } from "@/lib/useDocumentTitle";
import type { ApiFieldError, ApiProblem } from "@/lib/api";
import { formatDateTime, formatMoney } from "@/lib/format";
import type {
  OrderLine,
  OrderStatus,
  Shortage,
} from "@/features/orders/types";
import { orderStatusLabel } from "@/features/orders/types";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

const DRAFT_NOTE_TEXT = "Vista previa: la tasa se fija al confirmar.";
const REQUIRED_MESSAGE = "Este campo es obligatorio.";

/** The classes of a ledger header cell and a ledger body cell. */
const TABLE_HEAD_CLASSES = [
  "border-b-2 border-ink px-[10px] py-[9px] text-left",
  "text-xs font-medium uppercase tracking-[0.07em] text-muted",
].join(" ");

const TABLE_CELL_CLASSES =
  "border-b border-line px-[10px] py-[9px] text-ink tabular-nums";

/**
 * The badge colors of the theme: confirmed, paid and shipped carry the
 * positive shades; drafts and cancelled orders stay quiet. The label
 * carries the meaning; color never does on its own.
 */
function orderBadgeClasses(status: OrderStatus): string {
  const quiet = status === "draft" || status === "cancelled";
  return [
    "inline-flex rounded-sm px-2 py-0.5 text-xs font-semibold",
    quiet ? "bg-off-bg text-muted" : "bg-ok-bg text-accent",
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

/**
 * A quantity of the UI (correction B2): empty means "required" with no
 * request; a full digit string travels as an integer; anything else
 * (`"5.5"`, `"-1"`, text) travels as the typed string, so the server's
 * `INVALID_FORMAT` message shows on the field. No other client checks:
 * the strict integer rules are the server's (correction S2).
 */
function parseQuantity(raw: string): {
  value: number | string;
  requiredOnly: boolean;
} {
  const trimmed = raw.trim();
  if (trimmed === "") {
    return { value: trimmed, requiredOnly: true };
  }
  if (/^[0-9]+$/.test(trimmed)) {
    return { value: Number(trimmed), requiredOnly: false };
  }
  return { value: trimmed, requiredOnly: false };
}

/**
 * The first field error of `errors[]` whose field the caller owns, `null`
 * otherwise. The `field` member of a body error is exactly one of
 * `customer_id`, `product_id`, `quantity`, `version`, `tax_rate`
 * (correction S1).
 */
function fieldErrorOf(
  error: unknown,
  fields: readonly string[],
): ApiFieldError | null {
  if (!(error instanceof ApiRequestError)) {
    return null;
  }
  const entry = error.problem.errors?.find((listed) =>
    fields.includes(listed.field),
  );
  return entry ?? null;
}

/** A helper status line of the pickers ("Buscando clientes…" / empty). */
function PickerStatus({ testId, busy = false, children }: {
  testId: string;
  /** The loading status of a picker is a busy region. */
  busy?: boolean;
  children: string;
}) {
  return (
    <p
      role="status"
      data-testid={testId}
      aria-busy={busy ? "true" : undefined}
      className="mt-3 text-[13px] text-muted"
    >
      {children}
    </p>
  );
}

/** A plain (read-only) line row of the table. */
function StaticLineRow({ line }: { line: OrderLine }) {
  return (
    <tr data-testid={`orders-detail-line-row-${line.id}`} className="ledger-row">
      <td
        data-testid={`orders-detail-line-product-cell-${line.id}`}
        className={TABLE_CELL_CLASSES}
      >
        {line.name} ({line.sku})
      </td>
      <td
        data-testid={`orders-detail-line-quantity-cell-${line.id}`}
        className={TABLE_CELL_CLASSES}
      >
        {line.quantity}
      </td>
      <td
        data-testid={`orders-detail-line-price-cell-${line.id}`}
        className={TABLE_CELL_CLASSES}
      >
        {formatMoney(line.unit_price)}
      </td>
      <td
        data-testid={`orders-detail-line-total-cell-${line.id}`}
        className={TABLE_CELL_CLASSES}
      >
        {formatMoney(line.line_total)}
      </td>
    </tr>
  );
}

/** One order line with its own quantity editor (draft, can edit). */
function EditLineRow({ line, saving, removing, mutationsPending, pageFailureCount, sendLineFailureToPage, saveLine, removeLine }: {
  line: OrderLine;
  /** Whether this row's save (or removal) request runs. */
  saving: boolean;
  removing: boolean;
  /** B1: every mutation control of the page is disabled while any runs. */
  mutationsPending: boolean;
  /** One increment per failed submit anywhere on the page. */
  pageFailureCount: number;
  /** The failure the row cannot map onto its field goes to the page. */
  sendLineFailureToPage: (error: unknown) => void;
  /** The page sends the request: it owns the mutation and the version. */
  saveLine: (
    lineId: number,
    quantity: number | string,
  ) => Promise<void>;
  removeLine: (lineId: number) => Promise<void>;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [quantityInput, setQuantityInput] = useState(String(line.quantity));
  const [lineError, setLineError] = useState<string | null>(null);
  const [rowFailureCount, setRowFailureCount] = useState(0);

  // The input holds the error: the focus goes to it, on the first failure
  // and on every repetition.
  useEffect(() => {
    if (!lineError) {
      return;
    }
    inputRef.current?.focus();
  }, [lineError, rowFailureCount, pageFailureCount]);

  async function handleSave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (mutationsPending) {
      return;
    }
    const parsed = parseQuantity(quantityInput);
    if (parsed.requiredOnly) {
      setRowFailureCount((count) => count + 1);
      setLineError(REQUIRED_MESSAGE);
      return;
    }

    // Each submit clears the errors of the previous one.
    setLineError(null);
    try {
      await saveLine(line.id, parsed.value);
    } catch (error) {
      const mapped = fieldErrorOf(error, ["quantity"]);
      if (mapped === null) {
        sendLineFailureToPage(error);
      } else {
        setRowFailureCount((count) => count + 1);
        setLineError(mapped.message);
      }
    }
  }

  async function handleRemove() {
    if (mutationsPending) {
      return;
    }
    setLineError(null);
    try {
      await removeLine(line.id);
    } catch (error) {
      // A line removal has no field of its own: everything goes to the
      // form-level alert, which also refetches the order.
      sendLineFailureToPage(error);
    }
  }

  return (
    <tr data-testid={`orders-detail-line-row-${line.id}`} className="ledger-row">
      <td
        data-testid={`orders-detail-line-product-cell-${line.id}`}
        className={TABLE_CELL_CLASSES}
      >
        {line.name} ({line.sku})
      </td>
      <td
        data-testid={`orders-detail-line-quantity-cell-${line.id}`}
        className={TABLE_CELL_CLASSES}
      >
        {/*
         * The editor is a form of its own: "Guardar" submits it and a
         * second click is guarded by the page state.
         */}
        <form
          noValidate
          onSubmit={handleSave}
          data-testid={`orders-detail-line-form-${line.id}`}
          className="flex flex-wrap items-end gap-2"
        >
          <Input
            ref={inputRef}
            id={`orders-detail-line-quantity-input-${line.id}`}
            testId={`orders-detail-line-quantity-input-${line.id}`}
            label="Cantidad"
            type="number"
            hideLabel
            value={quantityInput}
            onChange={(event) => setQuantityInput(event.target.value)}
            error={lineError ?? undefined}
          />
          <Button
            testId={`orders-detail-line-save-button-${line.id}`}
            type="submit"
            loading={saving}
            disabled={mutationsPending}
          >
            Guardar
          </Button>
          <Button
            testId={`orders-detail-line-remove-button-${line.id}`}
            variant="secondary"
            loading={removing}
            disabled={mutationsPending}
            onClick={() => void handleRemove()}
          >
            Quitar
          </Button>
        </form>
      </td>
      <td
        data-testid={`orders-detail-line-price-cell-${line.id}`}
        className={TABLE_CELL_CLASSES}
      >
        {formatMoney(line.unit_price)}
      </td>
      <td
        data-testid={`orders-detail-line-total-cell-${line.id}`}
        className={TABLE_CELL_CLASSES}
      >
        {formatMoney(line.line_total)}
      </td>
    </tr>
  );
}

/** The collapsed "Cambiar cliente" section of a draft (correction B3). */
function ChangeCustomerPanel({ mutationsPending, pageFailureCount, changeCustomer, routePageError }: {
  mutationsPending: boolean;
  pageFailureCount: number;
  changeCustomer: (customerId: number) => Promise<void>;
  routePageError: (error: unknown) => void;
}) {
  const [open, setOpen] = useState(false);
  const [pickerQ, setPickerQ] = useState("");
  const [pickerInput, setPickerInput] = useState("");
  const customers = useCustomers({
    page: 1,
    q: pickerQ || undefined,
    status: "active",
  });

  const [customerId, setCustomerId] = useState("");
  const [selectError, setSelectError] = useState<string | null>(null);
  const [failureCount, setFailureCount] = useState(0);

  const selectInputId = "orders-detail-changecustomer-select";

  // B3: the choice never holds an id the select does not show; a render
  // correction, as in the create page, not a setState inside an effect.
  const [lastData, setLastData] = useState<CustomerList | undefined>(undefined);
  const pickerItems = customers.isSuccess ? customers.data.items : [];
  if (customers.data !== lastData) {
    setLastData(customers.data);
    if (
      customerId !== ""
      && !pickerItems.some((candidate) => String(candidate.id) === customerId)
    ) {
      setCustomerId("");
    }
  }

  // Focus after a failure of the change: the select with the field error.
  useEffect(() => {
    if (!selectError || !open) {
      return;
    }
    document.getElementById(selectInputId)?.focus();
  }, [selectError, failureCount, pageFailureCount, open]);

  function handleSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPickerQ(pickerInput.trim());
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (customerId === "" || mutationsPending) {
      return;
    }
    setSelectError(null);
    try {
      await changeCustomer(Number(customerId));
    } catch (error) {
      const mapped = fieldErrorOf(error, ["customer_id"]);
      if (mapped !== null) {
        setFailureCount((count) => count + 1);
        setSelectError(mapped.message);
      } else if (
        error instanceof ApiRequestError
        && error.problem.code === "CUSTOMER_INACTIVE"
      ) {
        setFailureCount((count) => count + 1);
        setSelectError(error.problem.detail);
      } else {
        routePageError(error);
      }
    }
  }

  function pickerProblemDetail(): string {
    if (customers.error instanceof ApiRequestError) {
      return customers.error.problem.detail;
    }
    return INTERNAL_ERROR_DETAIL;
  }

  return (
    <section className="mt-6">
      {/*
       * The toggle of the corrected review (B3): a real button with
       * `aria-expanded` and `aria-controls`, not a `<details>` element.
       */}
      <Button
        testId="orders-detail-changecustomer-button"
        variant="secondary"
        aria-expanded={open}
        aria-controls="orders-detail-changecustomer-panel"
        onClick={() => setOpen((current) => !current)}
      >
        Cambiar cliente
      </Button>

      <div
        id="orders-detail-changecustomer-panel"
        hidden={!open}
        className="mt-3 w-full max-w-[520px]"
      >
        {/*
         * The customer search is its own form, never nested inside the
         * form that submits (correction B3).
         */}
        <form
          data-testid="orders-detail-changecustomer-search-form"
          noValidate
          onSubmit={handleSearch}
          className="flex flex-wrap items-end gap-3"
        >
          <Input
            id="orders-detail-changecustomer-search"
            testId="orders-detail-changecustomer-search-input"
            label="Buscar cliente"
            value={pickerInput}
            onChange={(event) => setPickerInput(event.target.value)}
          />
          <Button
            testId="orders-detail-changecustomer-search-button"
            type="submit"
            variant="secondary"
          >
            Buscar
          </Button>
        </form>

        {customers.isPending ? (
          <PickerStatus busy testId="orders-detail-changecustomer-loading-status">
            Buscando clientes…
          </PickerStatus>
        ) : customers.isError ? (
          <div className="mt-3">
            <Alert testId="orders-detail-changecustomer-error-alert">
              {pickerProblemDetail()}
            </Alert>
            <div className="mt-3">
              <Button
                testId="orders-detail-changecustomer-retry-button"
                onClick={() => void customers.refetch()}
              >
                Reintentar
              </Button>
            </div>
          </div>
        ) : pickerItems.length === 0 ? (
          <PickerStatus testId="orders-detail-changecustomer-empty-status">
            No hay clientes activos que coincidan.
          </PickerStatus>
        ) : null}

        {selectError ? (
          <Alert testId="orders-detail-changecustomer-error-alert" tabIndex={-1}>
            {selectError}
          </Alert>
        ) : null}

        <form
          data-testid="orders-detail-changecustomer-form"
          noValidate
          onSubmit={handleSubmit}
          className="mt-3 flex flex-col gap-3"
        >
          <Select
            id={selectInputId}
            testId="orders-detail-changecustomer-select"
            label="Cliente"
            value={customerId}
            onChange={(event) => setCustomerId(event.target.value)}
            error={selectError ?? undefined}
          >
            <option value="" disabled>
              Elige un cliente
            </option>
            {pickerItems.map((candidate) => (
              <option key={candidate.id} value={candidate.id}>
                {candidate.name}
              </option>
            ))}
          </Select>
          <Button
            testId="orders-detail-changecustomer-submit-button"
            type="submit"
            loading={mutationsPending}
            disabled={customerId === "" || mutationsPending}
            className="w-full md:w-auto"
          >
            Cambiar
          </Button>
        </form>
      </div>
    </section>
  );
}

/** The detail of one order. */
function OrderDetail({ id }: { id: number }) {
  const me = useMe();
  const orderQuery = useOrder(id);
  const router = useRouter();

  // The tab: the section while the record is in the air (and while a
  // failed request is on screen), the order number after it arrives.
  useDocumentTitle(
    orderQuery.isSuccess ? `Pedido ${orderQuery.data.number}` : "Pedidos",
  );

  const setCustomer = useSetOrderCustomer();
  const addLine = useAddLine();
  const transition = useOrderTransition();
  const invoiceIssue = useIssueInvoice();
  const setLineQuantity = useSetLineQuantity();
  const removeLine = useRemoveLine();

  // This flag is the loading of the clicked row; the rows read it from
  // their props.
  const [savingLineId, setSavingLineId] = useState<number | null>(null);
  const [removingLineId, setRemovingLineId] = useState<number | null>(null);
  const [pendingTransition, setPendingTransition] = useState<
    "confirm" | "cancel" | "ship" | null
  >(null);
  // The confirmation of the destructive cancel (the dialog below): the
  // click opens it, the confirm runs the same transition as before.
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [pendingIssue, setPendingIssue] = useState(false);

  const [addProductId, setAddProductId] = useState("");
  const [addQuantity, setAddQuantity] = useState("1");
  const [addProductError, setAddProductError] = useState<string | null>(null);
  const [addQuantityError, setAddQuantityError] = useState<string | null>(null);

  const [alert, setAlert] = useState<string | null>(null);
  const [shortages, setShortages] = useState<Shortage[] | null>(null);
  const [pageFailureCount, setPageFailureCount] = useState(0);
  const formAlertRef = useRef<HTMLParagraphElement>(null);

  const order = orderQuery.data ?? null;
  const canEdit = me.data ? canEditOrders(me.data.role) : false;
  const canTransition = me.data ? canTransitionOrders(me.data.role) : false;
  const canInvoice = me.data ? canManageInvoices(me.data.role) : false;
  const editable = order?.status === "draft" && canEdit;

  // Only the editor of a draft needs the catalog, so a failing fetch
  // stays user visible only where the editor exists.
  const products = useProducts({ enabled: editable });

  // B1: while any mutation of the order is pending, every control that
  // sends one is disabled; all of them share the version, so a second
  // request sent before the first returns would only produce a
  // VERSION_CONFLICT of the user's own making.
  const mutationsPending =
    setCustomer.isPending
    || addLine.isPending
    || transition.isPending
    || invoiceIssue.isPending
    || setLineQuantity.isPending
    || removeLine.isPending;

  // Focus after a page-level failure: the alert when it is shown.
  useEffect(() => {
    if (!alert) {
      return;
    }
    formAlertRef.current?.focus();
  }, [alert, pageFailureCount]);

  /**
   * Every page-level failure lands here: its detail goes to the alert
   * (the shortages of an INSUFFICIENT_STOCK under it) and the order is
   * always refetched, so the next click sends a fresh version.
   */
  function routePageError(error: unknown): void {
    if (error instanceof ApiRequestError) {
      const problem: ApiProblem = error.problem;
      setAlert(problem.detail);
      if (problem.code === "INSUFFICIENT_STOCK") {
        setShortages((problem.shortages as Shortage[] | undefined) ?? []);
      } else {
        setShortages(null);
      }
    } else {
      setAlert(INTERNAL_ERROR_DETAIL);
      setShortages(null);
    }
    setPageFailureCount((count) => count + 1);
    void orderQuery.refetch();
  }

  // The line mutations: the page sends them, so all pending states and
  // the same version live in one place.
  async function saveLine(lineId: number, quantity: number | string) {
    if (!order) {
      return;
    }
    setSavingLineId(lineId);
    try {
      await setLineQuantity.mutateAsync({
        id: order.id,
        lineId,
        body: { quantity, version: order.version },
      });
    } finally {
      setSavingLineId(null);
    }
  }

  async function removeLineById(lineId: number): Promise<void> {
    if (!order) {
      return;
    }
    setRemovingLineId(lineId);
    try {
      await removeLine.mutateAsync({
        id: order.id,
        lineId,
        version: order.version,
      });
    } finally {
      setRemovingLineId(null);
    }
  }

  async function changeCustomer(customerId: number): Promise<void> {
    if (!order) {
      return;
    }
    await setCustomer.mutateAsync({
      id: order.id,
      body: { customer_id: customerId, version: order.version },
    });
  }

  async function handleAddLine(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!order || !canEdit) {
      return;
    }
    if (addProductId === "" || mutationsPending) {
      return;
    }
    const parsed = parseQuantity(addQuantity);
    if (parsed.requiredOnly) {
      setAddQuantityError(REQUIRED_MESSAGE);
      return;
    }

    // Each submit clears the errors of the previous one.
    setAddProductError(null);
    setAddQuantityError(null);
    try {
      await addLine.mutateAsync({
        id: order.id,
        body: {
          product_id: Number(addProductId),
          quantity: parsed.value,
          version: order.version,
        },
      });
      // The cache holds the new order; reset the form of the addition.
      setAddProductId("");
      setAddQuantity("1");
    } catch (error) {
      const productMapped = fieldErrorOf(error, ["product_id"]);
      if (productMapped !== null) {
        setAddProductError(productMapped.message);
        return;
      }
      const quantityMapped = fieldErrorOf(error, ["quantity"]);
      if (quantityMapped !== null) {
        setAddQuantityError(quantityMapped.message);
        return;
      }
      routePageError(error);
    }
  }

  async function handleTransition(
    action: "confirm" | "cancel" | "ship",
  ): Promise<void> {
    if (!order || !canTransition) {
      return;
    }
    if (mutationsPending || pendingTransition !== null) {
      return;
    }
    setPendingTransition(action);
    try {
      await transition.mutateAsync({
        id: order.id,
        action,
        version: order.version,
      });
    } catch (error) {
      // INVALID_TRANSITION, ORDER_EMPTY, CUSTOMER_INACTIVE,
      // ORDER_NOT_EDITABLE, VERSION_CONFLICT and INSUFFICIENT_STOCK all
      // route to the alert; the order is refetched inside it.
      routePageError(error);
    } finally {
      setPendingTransition(null);
      // The confirmation dialog of the cancel closes when the request
      // ends, failure or success: the answer is what the screen shows.
      if (action === "cancel") {
        setCancelDialogOpen(false);
      }
    }
  }

  /**
   * Issues the invoice of a confirmed order: POST /api/orders/{id}/invoice
   * with the version of the order on screen; the navigation goes to the
   * new invoice. The four failure codes of the brief (ORDER_NOT_INVOICEABLE,
   * CUSTOMER_TAX_ID_REQUIRED, INVOICE_ALREADY_EXISTS and VERSION_CONFLICT)
   * route to the existing order alert, which refetches the order.
   */
  async function handleIssueInvoice(): Promise<void> {
    if (!order || !canInvoice) {
      return;
    }
    if (order.status !== "confirmed" || order.invoice_id !== null) {
      return;
    }
    if (mutationsPending || pendingIssue) {
      return;
    }
    setPendingIssue(true);
    try {
      const invoice = await invoiceIssue.mutateAsync({
        orderId: order.id,
        version: order.version,
      });
      router.push(`/invoices/${invoice.id}`);
    } catch (error) {
      routePageError(error);
    } finally {
      setPendingIssue(false);
    }
  }

  if (orderQuery.isPending) {
    return (
      <p
        role="status"
        data-testid="orders-detail-loading-status"
        aria-busy="true"
        className="text-muted"
      >
        Cargando…
      </p>
    );
  }

  if (orderQuery.isError) {
    const problem = orderQuery.error instanceof ApiRequestError
      ? orderQuery.error.problem
      : { status: 0, detail: INTERNAL_ERROR_DETAIL };
    const is404 = problem.status === 404;

    return (
      <div>
        <Alert testId="orders-detail-error-alert">
          {problem.detail}
        </Alert>
        <div className="mt-3">
          {is404 ? null : (
            <Button
              testId="orders-detail-retry-button"
              onClick={() => void orderQuery.refetch()}
            >
              Reintentar
            </Button>
          )}
        </div>
        <div className="mt-3">
          <Link href="/orders" testId="orders-detail-back-link">
            Volver a pedidos
          </Link>
        </div>
      </div>
    );
  }

  const lines = order?.lines ?? [];
  const productsInOrder = new Set(lines.map((line) => line.product_id));
  const productItems = products.isSuccess
    ? products.data.items
    : [];

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 data-testid="orders-detail-heading">{order?.number}</h1>
        {order ? (
          <span
            data-testid="orders-detail-state-status"
            className={orderBadgeClasses(order.status)}
          >
            {orderStatusLabel(order.status)}
          </span>
        ) : null}
      </div>

      {alert ? (
        <div className="mt-3">
          <Alert
            ref={formAlertRef}
            testId="orders-detail-alert"
            tabIndex={-1}
          >
            {alert}
          </Alert>
          {shortages !== null && shortages.length > 0 ? (
            <ul
              data-testid="orders-detail-shortages-list"
              className="mt-3 flex flex-col gap-1"
            >
              {shortages.map((shortage) => (
                <li
                  key={shortage.product_id}
                  data-testid={`orders-detail-shortage-item-${shortage.product_id}`}
                  className="text-[13px] font-medium text-danger"
                >
                  {shortage.name} ({shortage.sku}): disponible{" "}
                  {shortage.available}, solicitado {shortage.requested}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      <ConfirmDialog
        open={cancelDialogOpen}
        title={`¿Cancelar el pedido ${order?.number ?? ""}?`}
        titleId="orders-cancel-title"
        messageId="orders-cancel-message"
        testId="orders-cancel-confirm-dialog"
        titleTestId="orders-cancel-title-heading"
        messageTestId="orders-cancel-message-text"
        confirmTestId="orders-cancel-confirm-button"
        cancelTestId="orders-cancel-back-button"
        confirmLabel="Sí, cancelar pedido"
        pending={pendingTransition === "cancel"}
        onConfirm={() => void handleTransition("cancel")}
        onCancel={() => setCancelDialogOpen(false)}
      >
        {order?.status === "confirmed"
          ? "El stock reservado vuelve al inventario y la factura emitida, si existe, se anula."
          : "El borrador quedará cancelado."}
      </ConfirmDialog>

      {/* The facts of the order in a surface card. */}
      <div className="mt-6 rounded-lg border border-line bg-surface p-5">
        <dl className="flex flex-col gap-3">
          <DetailRow label="Cliente">
            <dd>
              <Link
                href={`/customers/${order?.customer.id}`}
                testId="orders-detail-customer-link"
                className="break-words"
              >
                {order?.customer.name}
                {order?.customer.status === "inactive" ? " (inactivo)" : ""}
              </Link>
            </dd>
          </DetailRow>
          <DetailRow label="Creado">
            <dd
              data-testid="orders-detail-created-text"
              className="break-words tabular-nums"
            >
              {order ? formatDateTime(order.created_at) : ""}
            </dd>
          </DetailRow>
          <DetailRow label="Actualizado">
            <dd
              data-testid="orders-detail-updated-text"
              className="break-words tabular-nums"
            >
              {order ? formatDateTime(order.updated_at) : ""}
            </dd>
          </DetailRow>
          {order?.invoice_id !== null ? (
            <DetailRow label="Factura">
              <dd>
                <Link
                  href={`/invoices/${order?.invoice_id}`}
                  testId="orders-detail-invoice-link"
                >
                  Ver factura
                </Link>
              </dd>
            </DetailRow>
          ) : null}
        </dl>
      </div>

      {/* The lines of the order with the totals under them. */}
      <div className="mt-6 rounded-lg border border-line bg-surface p-5">
        <h2 data-testid="orders-detail-lines-heading" className="text-lg font-semibold">
          Líneas
        </h2>
        {lines.length === 0 ? (
          <p
            data-testid="orders-detail-nolines-text"
            className="mt-3 text-muted"
          >
            Este pedido aún no tiene líneas.
          </p>
        ) : (
          <div className="mt-3 overflow-x-auto p-1.5">
            <table
              data-testid="orders-detail-lines-table"
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
                {lines.map((line) =>
                  editable ? (
                    // A change of the line remounts the row and resets its
                    // editor to the server values.
                    <EditLineRow
                      key={`${line.id}-${line.quantity}-${line.unit_price}`}
                      line={line}
                      saving={savingLineId === line.id}
                      removing={removingLineId === line.id}
                      mutationsPending={mutationsPending}
                      pageFailureCount={pageFailureCount}
                      sendLineFailureToPage={routePageError}
                      saveLine={saveLine}
                      removeLine={removeLineById}
                    />
                  ) : (
                    <StaticLineRow key={line.id} line={line} />
                  ),
                )}
              </tbody>
            </table>
          </div>
        )}

        {/*
         * The totals of the order: the ledger with the double rule above
         * the total.
         */}
        <div className="mt-4 flex flex-col items-end gap-1 text-right">
          <p className="flex gap-4 tabular-nums">
            <span className="font-medium text-muted">Subtotal</span>
            <span data-testid="orders-detail-subtotal-text">
              {order ? formatMoney(order.subtotal) : ""}
            </span>
          </p>
          <p className="flex gap-4 tabular-nums">
            <span
              data-testid="orders-detail-taxrate-text"
              className="font-medium text-muted"
            >
              Impuesto ({order?.tax_rate} %)
            </span>
            <span data-testid="orders-detail-tax-text">
              {order ? formatMoney(order.tax) : ""}
            </span>
          </p>
          <div className="flex gap-4 border-t-4 border-double border-ink pt-2 tabular-nums">
            <span className="font-semibold">Total</span>
            <span
              data-testid="orders-detail-total-text"
              className="font-semibold"
            >
              {order ? formatMoney(order.total) : ""}
            </span>
          </div>
          {order?.status === "draft" ? (
            <p
              data-testid="orders-detail-preview-text"
              className="mt-1 text-[13px] text-muted"
            >
              {DRAFT_NOTE_TEXT}
            </p>
          ) : null}
        </div>
      </div>

      {/* Add a line: only in a draft, for users who can edit. */}
      {editable ? (
        <section className="mt-6">
          <h2
            data-testid="orders-detail-addline-heading"
            className="text-lg font-semibold"
          >
            Agregar una línea
          </h2>
          {products.isError ? (
            <div className="mt-3">
              <Alert testId="orders-detail-products-error-alert">
                {products.error instanceof ApiRequestError
                  ? products.error.problem.detail
                  : INTERNAL_ERROR_DETAIL}
              </Alert>
              <div className="mt-3">
                <Button
                  testId="orders-detail-products-retry-button"
                  onClick={() => void products.refetch()}
                >
                  Reintentar
                </Button>
              </div>
            </div>
          ) : (
            <form
              noValidate
              onSubmit={handleAddLine}
              data-testid="orders-detail-addline-form"
              className="mt-3 flex flex-wrap items-end gap-3"
            >
              {/*
               * Correction B4: a disabled placeholder while up; the only
               * option during the catalog load says "Cargando products…".
               */}
              <Select
                id="orders-detail-addline-product"
                testId="orders-detail-addline-product-select"
                label="Producto"
                value={addProductId}
                onChange={(event) => setAddProductId(event.target.value)}
                error={addProductError ?? undefined}
              >
                {products.isPending ? (
                  <option value="">Cargando productos…</option>
                ) : (
                  <option value="" disabled>
                    Elige un producto
                  </option>
                )}
                {productItems.map((product) => (
                  <option
                    key={product.id}
                    value={product.id}
                    disabled={productsInOrder.has(product.id)}
                  >
                    {`${product.name} (${product.sku}) — ${formatMoney(product.price)} — stock ${product.stock}`}
                  </option>
                ))}
              </Select>
              <Input
                id="orders-detail-addline-quantity"
                testId="orders-detail-addline-quantity-input"
                label="Cantidad"
                type="number"
                value={addQuantity}
                onChange={(event) => setAddQuantity(event.target.value)}
                error={addQuantityError ?? undefined}
              />
              <Button
                testId="orders-detail-addline-submit-button"
                type="submit"
                loading={addLine.isPending}
                disabled={mutationsPending || addProductId === ""}
              >
                Agregar
              </Button>
            </form>
          )}
        </section>
      ) : null}

      {/* Change the customer: only in a draft, for users who can edit. */}
      {editable && order ? (
        <ChangeCustomerPanel
          mutationsPending={mutationsPending}
          pageFailureCount={pageFailureCount}
          changeCustomer={changeCustomer}
          routePageError={routePageError}
        />
      ) : null}

      {/* Transitions, only for the roles that can do them. */}
      {canTransition
      && order
      && (order.status === "draft"
        || order.status === "confirmed"
        || order.status === "paid") ? (
        <div className="mt-6 flex flex-wrap items-center gap-3">
          {order.status === "draft" ? (
            <Button
              testId="orders-detail-confirm-button"
              loading={pendingTransition === "confirm"}
              disabled={mutationsPending}
              onClick={() => void handleTransition("confirm")}
            >
              Confirmar
            </Button>
          ) : null}
          {order.status === "draft" || order.status === "confirmed" ? (
            <Button
              testId="orders-detail-cancel-button"
              variant="secondary"
              disabled={mutationsPending}
              onClick={() => setCancelDialogOpen(true)}
            >
              Cancelar pedido
            </Button>
          ) : null}
          {order.status === "paid" ? (
            <Button
              testId="orders-detail-ship-button"
              loading={pendingTransition === "ship"}
              disabled={mutationsPending}
              onClick={() => void handleTransition("ship")}
            >
              Marcar como enviado
            </Button>
          ) : null}
        </div>
      ) : null}

      {/* Issue the invoice: Admin and Finance on a confirmed order with
          no invoice; the navigation goes to the new invoice. Same vertical
          spacing as the other action rows. */}
      {canInvoice
      && order
      && order.status === "confirmed"
      && order.invoice_id === null ? (
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Button
            testId="orders-detail-invoice-button"
            loading={pendingIssue}
            disabled={mutationsPending}
            onClick={() => void handleIssueInvoice()}
          >
            Facturar
          </Button>
        </div>
      ) : null}

      <div className="mt-6">
        <Link href="/orders" testId="orders-detail-back-link">
          Volver a pedidos
        </Link>
      </div>
    </div>
  );
}

export default function OrderDetailPage() {
  // The section title covers the invalid-id screen too; the content
  // component replaces it with the order number once it arrives.
  useDocumentTitle("Pedidos");
  const id = parseOrderIdParam(useParams().id);

  if (id === null) {
    // Not a valid id: show the not-found alert and the back link without
    // calling the API.
    return (
      <div>
        <Alert testId="orders-detail-error-alert">
          No se encontró el recurso solicitado.
        </Alert>
        <div className="mt-3">
          <Link href="/orders" testId="orders-detail-back-link">
            Volver a pedidos
          </Link>
        </div>
      </div>
    );
  }

  return <OrderDetail id={id} />;
}
