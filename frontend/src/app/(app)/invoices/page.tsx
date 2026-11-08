"use client";

import {
  Alert,
  Button,
  Input,
  Link,
  Select,
  SortableHeader,
  type SortableHeaderState,
  TableScroll,
} from "@/components/ui";
import { useInvoices } from "@/features/invoices/hooks";
import {
  flipInvoiceSortDirection,
  invoiceSortDefaultDirection,
  invoiceSortLabel,
  isDefaultInvoiceSort,
  parseInvoiceListParams,
  resolveInvoiceSort,
  type InvoiceSort,
  type InvoiceSortField,
} from "@/features/invoices/params";
import {
  invoiceStatusLabel,
} from "@/features/invoices/types";
import { ApiRequestError, INTERNAL_ERROR_DETAIL } from "@/lib/api";
import { useDocumentTitle } from "@/lib/useDocumentTitle";
import { formatDate, formatMoney } from "@/lib/format";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";

/**
 * The list URL of the screen: page (always) plus the search values and
 * the sort when it is not the plain-list one. This is what every
 * navigation writes, so links can be shared.
 */
function listUrl(
  page: number,
  q: string | null,
  status: string | null,
  sort: InvoiceSort,
): string {
  const search = new URLSearchParams();
  search.set("page", String(page));
  if (q) {
    search.set("q", q);
  }
  if (status) {
    search.set("status", status);
  }
  if (!isDefaultInvoiceSort(sort)) {
    search.set("sort", sort.sort);
    search.set("direction", sort.direction);
  }
  return `/invoices?${search.toString()}`;
}

/** The classes of a ledger header cell and a ledger body cell. */
const TABLE_HEAD_CLASSES = [
  "border-b-2 border-ink px-[10px] py-[9px] text-left",
  "text-xs font-medium uppercase tracking-[0.07em] text-muted",
].join(" ");

const TABLE_CELL_CLASSES =
  "border-b border-line px-[10px] py-[9px] text-ink tabular-nums";

const STATE_BADGE_CLASSES = [
  "inline-flex rounded-sm px-2 py-0.5 text-xs font-semibold",
  // Paid invoices carry the positive shade; issued and void stay quiet.
  "bg-ok-bg text-accent",
].join(" ");

const STATE_MUTED_BADGE_CLASSES = [
  "inline-flex rounded-sm px-2 py-0.5 text-xs font-semibold",
  "bg-off-bg text-muted",
].join(" ");

function badgeClasses(status: string): string {
  return status === "paid"
    ? STATE_BADGE_CLASSES
    : STATE_MUTED_BADGE_CLASSES;
}

/** The last page for a total: `Y = max(1, ceil(total / 20))`. */
function lastPage(total: number, pageSize: number): number {
  return Math.max(1, Math.ceil(total / pageSize));
}

function InvoicesListContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const params = parseInvoiceListParams(searchParams);
  // The resolved sort is stable while the URL values are (see the
  // customers list): the correction effect must not repeat itself.
  const sort = useMemo(
    () =>
      resolveInvoiceSort({
        sort: params.sort,
        direction: params.direction,
      }),
    [params.sort, params.direction],
  );
  // The default order travels without parameters: both the URL and the
  // list request stay the ones of the plain list.
  const sortRequest = isDefaultInvoiceSort(sort)
    ? {}
    : { sort: sort.sort, direction: sort.direction };
  const list = useInvoices({
    page: params.page,
    q: params.q ?? undefined,
    status: params.status ?? undefined,
    ...sortRequest,
  });

  // The fields of the search form are local; submitting them writes the
  // URL, which is what the list request reads.
  const [qInput, setQInput] = useState(params.q ?? "");
  const [statusInput, setStatusInput] = useState(params.status ?? "");

  // The URL is the state: arriving from a link (or a correction) resets
  // the fields during render, instead of watching the URL in an effect.
  const [lastUrlQ, setLastUrlQ] = useState(params.q);
  if (lastUrlQ !== params.q) {
    setLastUrlQ(params.q);
    setQInput(params.q ?? "");
  }
  const [lastUrlStatus, setLastUrlStatus] = useState(params.status);
  if (lastUrlStatus !== params.status) {
    setLastUrlStatus(params.status);
    setStatusInput(params.status ?? "");
  }

  const data = list.isSuccess && list.data !== undefined ? list.data : null;

  // A page beyond the last one is corrected in the URL instead of showing
  // an empty page next to "Página 99 de 3".
  useEffect(() => {
    if (!data) {
      return;
    }
    const last = lastPage(data.total, data.page_size);
    if (params.page <= last) {
      return;
    }
    router.replace(listUrl(last, params.q, params.status, sort));
  }, [data, params.page, params.q, params.status, sort, router]);

  function handleSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // Submitting goes back to page 1 with the trimmed values.
    router.push(listUrl(1, qInput.trim() || null, statusInput || null, sort));
  }

  function goToPage(page: number) {
    router.push(listUrl(page, params.q, params.status, sort));
  }

  /**
   * Sorting from a header: a new column sorts with the default direction
   * of its field (`created_at` descending), the sorted one flips; either
   * way the page goes back to 1 and the filters stay.
   */
  function toggleSort(field: InvoiceSortField) {
    const next: InvoiceSort = field === sort.sort
      ? {
        sort: field,
        direction: flipInvoiceSortDirection(sort.direction),
      }
      : { sort: field, direction: invoiceSortDefaultDirection(field) };
    router.push(listUrl(1, params.q, params.status, next));
  }

  /** The header state of one sortable column, the `aria-sort` value. */
  function headerState(field: InvoiceSortField): SortableHeaderState {
    if (sort.sort !== field) {
      return "none";
    }
    return sort.direction === "asc" ? "ascending" : "descending";
  }

  function problemDetail(): string {
    if (list.error instanceof ApiRequestError) {
      return list.error.problem.detail;
    }
    return INTERNAL_ERROR_DETAIL;
  }

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 data-testid="invoices-list-heading">Facturas</h1>
        {/*
         * There is no "new invoice" button: invoices are issued from the
         * order.
         */}
      </div>

      {/*
       * The live announcement of the order of the table (the same one the
       * other lists have), hidden from the visual layout.
       */}
      <p
        role="status"
        data-testid="invoices-list-sort-text"
        className="sr-only"
      >
        {`Ordenado por ${invoiceSortLabel(sort.sort)}, ${
          sort.direction === "asc" ? "ascendente" : "descendente"
        }`}
      </p>

      <form
        data-testid="invoices-list-search-form"
        onSubmit={handleSearch}
        className="mt-4 grid items-end gap-3 md:grid-cols-[minmax(0,1fr)_minmax(140px,220px)_auto]"
      >
        <Input
          id="invoices-list-search"
          testId="invoices-list-search-input"
          label="Buscar"
          placeholder="Número o cliente"
          value={qInput}
          onChange={(event) => setQInput(event.target.value)}
        />
        <Select
          id="invoices-list-status"
          testId="invoices-list-status-select"
          label="Estado"
          value={statusInput}
          onChange={(event) => setStatusInput(event.target.value)}
        >
          <option value="">Todas</option>
          <option value="issued">Emitidas</option>
          <option value="paid">Pagadas</option>
          <option value="void">Anuladas</option>
        </Select>
        <Button
          testId="invoices-list-search-button"
          type="submit"
          variant="secondary"
        >
          Buscar
        </Button>
      </form>

      {list.isPending ? (
        <p
          role="status"
          data-testid="invoices-list-loading-status"
          aria-busy="true"
          className="mt-6 text-muted"
        >
          Cargando…
        </p>
      ) : list.isError ? (
        <div className="mt-6">
          <Alert testId="invoices-list-error-alert">
            {problemDetail()}
          </Alert>
          <div className="mt-3">
            <Button
              testId="invoices-list-retry-button"
              onClick={() => void list.refetch()}
            >
              Reintentar
            </Button>
          </div>
        </div>
      ) : data !== null && data.items.length === 0 ? (
        <p
          role="status"
          data-testid="invoices-list-empty-status"
          className="mt-6 text-muted"
        >
          No hay facturas que coincidan.
        </p>
      ) : data !== null ? (
        <>
          {/*
           * The wide content scrolls inside this wrapper, never the page:
           * the padding keeps the 3px focus ring visible around the
           * scrollbar edges.
           */}
          <TableScroll testId="invoices-list-scroll-region" label="Tabla de facturas" className="mt-6">
            <table
              data-testid="invoices-list-table"
              className="min-w-[44rem] w-full"
            >
              <thead>
                <tr>
                  <SortableHeader
                    label="Número"
                    testId="invoices-list-sort-number-button"
                    state={headerState("number")}
                    className={TABLE_HEAD_CLASSES}
                    onClick={() => toggleSort("number")}
                  />
                  <th scope="col" className={TABLE_HEAD_CLASSES}>Pedido</th>
                  <SortableHeader
                    label="Cliente"
                    testId="invoices-list-sort-customer-button"
                    state={headerState("customer")}
                    className={TABLE_HEAD_CLASSES}
                    onClick={() => toggleSort("customer")}
                  />
                  <th scope="col" className={TABLE_HEAD_CLASSES}>Estado</th>
                  <SortableHeader
                    label="Total"
                    testId="invoices-list-sort-total-button"
                    state={headerState("total")}
                    className={TABLE_HEAD_CLASSES}
                    onClick={() => toggleSort("total")}
                  />
                  <SortableHeader
                    label="Creada"
                    testId="invoices-list-sort-created-button"
                    state={headerState("created_at")}
                    className={TABLE_HEAD_CLASSES}
                    onClick={() => toggleSort("created_at")}
                  />
                </tr>
              </thead>
              <tbody>
                {data.items.map((invoice) => (
                  <tr
                    key={invoice.id}
                    data-testid={`invoices-list-row-${invoice.id}`}
                    className="ledger-row"
                  >
                    <td
                      data-testid={`invoices-list-number-cell-${invoice.id}`}
                      className={TABLE_CELL_CLASSES}
                    >
                      <Link
                        href={`/invoices/${invoice.id}`}
                        testId={`invoices-list-view-link-${invoice.id}`}
                        className="font-medium"
                      >
                        {invoice.number}
                      </Link>
                    </td>
                    <td
                      data-testid={`invoices-list-order-cell-${invoice.id}`}
                      className={TABLE_CELL_CLASSES}
                    >
                      <Link
                        href={`/orders/${invoice.order_id}`}
                        testId={`invoices-list-order-link-${invoice.id}`}
                      >
                        {invoice.order_number}
                      </Link>
                    </td>
                    <td
                      data-testid={`invoices-list-customer-cell-${invoice.id}`}
                      className={TABLE_CELL_CLASSES}
                    >
                      {invoice.customer_name}
                    </td>
                    <td
                      data-testid={`invoices-list-state-cell-${invoice.id}`}
                      className={`${TABLE_CELL_CLASSES} whitespace-nowrap`}
                    >
                      <span className={badgeClasses(invoice.status)}>
                        {invoiceStatusLabel(invoice.status)}
                      </span>
                    </td>
                    <td
                      data-testid={`invoices-list-total-cell-${invoice.id}`}
                      className={`${TABLE_CELL_CLASSES} whitespace-nowrap text-right`}
                    >
                      {formatMoney(invoice.total)}
                    </td>
                    <td
                      data-testid={`invoices-list-created-cell-${invoice.id}`}
                      className={`${TABLE_CELL_CLASSES} whitespace-nowrap`}
                    >
                      {formatDate(invoice.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableScroll>

          {/*
           * The ledger footer: a 4px double rule of ink above it, the
           * total on the left and the pagination on the right.
           */}
          <div
            data-testid="invoices-list-footer-item"
            className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t-4 border-double border-ink pt-3"
          >
            <p
              data-testid="invoices-list-total-text"
              className="font-semibold tabular-nums"
            >
              {data.total === 1 ? "1 factura" : `${data.total} facturas`}
            </p>
            <nav
              aria-label="Paginación de facturas"
              className="flex flex-wrap items-center gap-3"
            >
              <Button
                testId="invoices-list-prev-button"
                variant="secondary"
                disabled={params.page <= 1}
                onClick={() => goToPage(params.page - 1)}
              >
                Anterior
              </Button>
              <p
                data-testid="invoices-list-page-text"
                className="tabular-nums"
              >
                {`Página ${params.page} de ${lastPage(data.total, data.page_size)}`}
              </p>
              <Button
                testId="invoices-list-next-button"
                variant="secondary"
                disabled={params.page >= lastPage(data.total, data.page_size)}
                onClick={() => goToPage(params.page + 1)}
              >
                Siguiente
              </Button>
            </nav>
          </div>
        </>
      ) : null}
    </div>
  );
}

export default function InvoicesPage() {
  useDocumentTitle("Facturas");

  return (
    <Suspense
      fallback={
        <p
          role="status"
          data-testid="invoices-list-loading-status"
          aria-busy="true"
        >
          Cargando…
        </p>
      }
    >
      <InvoicesListContent />
    </Suspense>
  );
}
