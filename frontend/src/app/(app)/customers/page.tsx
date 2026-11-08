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
  TEXT_LINK_CLASSES,
} from "@/components/ui";
import { useMe } from "@/features/auth/hooks";
import { useCustomers } from "@/features/customers/hooks";
import {
  customerSortDefaultDirection,
  customerSortLabel,
  customersExportUrl,
  flipCustomerSortDirection,
  isDefaultCustomerSort,
  parseCustomerListParams,
  resolveCustomerSort,
  type CustomerSort,
  type CustomerSortField,
} from "@/features/customers/params";
import { canManageCustomers } from "@/features/customers/permissions";
import { statusLabel } from "@/features/customers/types";
import { ApiRequestError, INTERNAL_ERROR_DETAIL } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { useDocumentTitle } from "@/lib/useDocumentTitle";
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
  sort: CustomerSort,
): string {
  const search = new URLSearchParams();
  search.set("page", String(page));
  if (q) {
    search.set("q", q);
  }
  if (status) {
    search.set("status", status);
  }
  if (!isDefaultCustomerSort(sort)) {
    search.set("sort", sort.sort);
    search.set("direction", sort.direction);
  }
  return `/customers?${search.toString()}`;
}

/** The classes of a ledger header cell and a ledger body cell. */
const TABLE_HEAD_CLASSES = [
  "border-b-2 border-ink px-[10px] py-[9px] text-left",
  "text-xs font-medium uppercase tracking-[0.07em] text-muted",
].join(" ");

const TABLE_CELL_CLASSES =
  "border-b border-line px-[10px] py-[9px] text-ink tabular-nums";

/** The ID fiscal and Estado cells must not wrap in the middle of a code. */
const TABLE_CELL_NOWRAP_CLASSES = `${TABLE_CELL_CLASSES} whitespace-nowrap`;

function CustomersListContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const me = useMe();

  const params = parseCustomerListParams(searchParams);
  // The resolved sort is stable while the URL values are: the correction
  // effect below must not re-run for a new object of the same pair.
  const sort = useMemo(
    () =>
      resolveCustomerSort({
        sort: params.sort,
        direction: params.direction,
      }),
    [params.sort, params.direction],
  );
  // The default order travels without parameters: both the URL and the
  // list request stay the ones of the plain list.
  const sortRequest = isDefaultCustomerSort(sort)
    ? {}
    : { sort: sort.sort, direction: sort.direction };
  const list = useCustomers({
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
  // the fields during render — the documented "adjust state when its
  // dependencies change" pattern — instead of watching the URL in an
  // effect.
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
  // an empty page next to "Página 99 de 3". Y = max(1, ceil(total/20));
  // the same correction covers a filter whose result ends before the
  // page the URL still carries.
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
  function toggleSort(field: CustomerSortField) {
    const next: CustomerSort = field === sort.sort
      ? {
        sort: field,
        direction: flipCustomerSortDirection(sort.direction),
      }
      : { sort: field, direction: customerSortDefaultDirection(field) };
    router.push(listUrl(1, params.q, params.status, next));
  }

  /** The header state of one sortable column, the `aria-sort` value. */
  function headerState(field: CustomerSortField): SortableHeaderState {
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

  const user = me.data;
  const canManage = user ? canManageCustomers(user.role) : false;

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 data-testid="customers-list-heading">Clientes</h1>

        {canManage ? (
          <>
            <Link href="/customers/import" testId="customers-list-import-link">
              Importar CSV
            </Link>
            <Link href="/customers/new" testId="customers-list-new-link" variant="primary">
              Nuevo cliente
            </Link>
          </>
        ) : null}
      </div>

      {/*
       * The live announcement of the order of the table: a screen reader
       * reads it each time the sort changes. It is the text the tests
       * assert on, hidden from the visual layout.
       */}
      <p
        role="status"
        data-testid="customers-list-sort-text"
        className="sr-only"
      >
        {`Ordenado por ${customerSortLabel(sort.sort)}, ${
          sort.direction === "asc" ? "ascendente" : "descendente"
        }`}
      </p>

      <form
        data-testid="customers-list-search-form"
        onSubmit={handleSearch}
        className="mt-4 grid items-end gap-3 md:grid-cols-[minmax(0,1fr)_minmax(140px,220px)_auto]"
      >
        <Input
          id="customers-list-search"
          testId="customers-list-search-input"
          label="Buscar"
          value={qInput}
          onChange={(event) => setQInput(event.target.value)}
        />
        <Select
          id="customers-list-status"
          testId="customers-list-status-select"
          label="Estado"
          value={statusInput}
          onChange={(event) => setStatusInput(event.target.value)}
        >
          <option value="">Todos</option>
          <option value="active">Activos</option>
          <option value="inactive">Inactivos</option>
        </Select>
        <Button
          testId="customers-list-search-button"
          type="submit"
          variant="secondary"
        >
          Buscar
        </Button>
      </form>

      {/*
       * The download of every customer the applied filters select: a
       * plain anchor (the API serves the file, the client router must
       * not touch it) with the state of the URL, never the text still
       * in the inputs. It renders in every state of the request, even
       * empty or error: an empty filter exports a file with the header
       * only. The DOM order keeps it right after the filter controls.
       */}
      <p className="mt-3">
        <a
          data-testid="customers-list-export-link"
          download
          href={customersExportUrl(params)}
          className={TEXT_LINK_CLASSES}
        >
          Exportar CSV
        </a>
      </p>

      {list.isPending ? (
        <p
          role="status"
          data-testid="customers-list-loading-status"
          aria-busy="true"
          className="mt-6 text-muted"
        >
          Cargando…
        </p>
      ) : list.isError ? (
        <div className="mt-6">
          <Alert testId="customers-list-error-alert">
            {problemDetail()}
          </Alert>
          <div className="mt-3">
            <Button
              testId="customers-list-retry-button"
              onClick={() => void list.refetch()}
            >
              Reintentar
            </Button>
          </div>
        </div>
      ) : data !== null && data.items.length === 0 ? (
        <p
          role="status"
          data-testid="customers-list-empty-status"
          className="mt-6 text-muted"
        >
          No hay clientes que coincidan.
        </p>
      ) : data !== null ? (
        <>
          {/*
           * The first load keeps the loading text; once the table holds
           * data, a new page, sort or filter keeps it on screen
           * (`keepPreviousData` in the hook) and the region announces the
           * new request with `aria-busy`, so a keyboard focus inside it
           * survives the change.
           */}
          <TableScroll testId="customers-list-scroll-region" label="Tabla de clientes" className="mt-6" busy={list.isFetching}>
            <table
              data-testid="customers-list-table"
              className="min-w-[40rem]"
            >
              <thead>
                <tr>
                  <SortableHeader
                    label="Nombre"
                    testId="customers-list-sort-name-button"
                    state={headerState("name")}
                    className={TABLE_HEAD_CLASSES}
                    onClick={() => toggleSort("name")}
                  />
                  <SortableHeader
                    label="Email"
                    testId="customers-list-sort-email-button"
                    state={headerState("email")}
                    className={TABLE_HEAD_CLASSES}
                    onClick={() => toggleSort("email")}
                  />
                  <th scope="col" className={TABLE_HEAD_CLASSES}>ID fiscal</th>
                  <th scope="col" className={TABLE_HEAD_CLASSES}>Estado</th>
                  <SortableHeader
                    label="Creado"
                    testId="customers-list-sort-created-button"
                    state={headerState("created_at")}
                    className={TABLE_HEAD_CLASSES}
                    onClick={() => toggleSort("created_at")}
                  />
                </tr>
              </thead>
              <tbody>
                {data.items.map((customer) => (
                  <tr
                    key={customer.id}
                    data-testid={`customers-list-row-${customer.id}`}
                    className="ledger-row"
                  >
                    <td
                      data-testid={`customers-list-name-cell-${customer.id}`}
                      className={TABLE_CELL_CLASSES}
                    >
                      <Link
                        href={`/customers/${customer.id}`}
                        testId={`customers-list-view-link-${customer.id}`}
                        className="font-medium"
                      >
                        {customer.name}
                      </Link>
                    </td>
                    <td
                      data-testid={`customers-list-email-cell-${customer.id}`}
                      className={TABLE_CELL_CLASSES}
                    >
                      {customer.email}
                    </td>
                    <td
                      data-testid={`customers-list-taxid-cell-${customer.id}`}
                      className={TABLE_CELL_NOWRAP_CLASSES}
                    >
                      {customer.tax_id ?? <span className="text-muted">—</span>}
                    </td>
                    <td
                      data-testid={`customers-list-state-cell-${customer.id}`}
                      className={TABLE_CELL_NOWRAP_CLASSES}
                    >
                      <span
                        className={[
                          "inline-flex rounded-sm px-2 py-0.5 text-xs font-semibold",
                          customer.status === "active"
                            ? "bg-ok-bg text-accent"
                            : "bg-off-bg text-muted",
                        ].join(" ")}
                      >
                        {statusLabel(customer.status)}
                      </span>
                    </td>
                    <td
                      data-testid={`customers-list-created-cell-${customer.id}`}
                      className={`${TABLE_CELL_CLASSES} whitespace-nowrap`}
                    >
                      {formatDate(customer.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableScroll>

          {/*
           * The ledger footer: a 4px double rule of ink above it, the
           * total on the left and the pagination on the right. The total
           * lives in this footer item, not inside the pagination nav.
           */}
          <div
            data-testid="customers-list-footer-item"
            className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t-4 border-double border-ink pt-3"
          >
            <p
              data-testid="customers-list-total-text"
              className="font-semibold tabular-nums"
            >
              {data.total === 1 ? "1 cliente" : `${data.total} clientes`}
            </p>
            <nav
              aria-label="Paginación de clientes"
              className="flex flex-wrap items-center gap-3"
            >
              <Button
                testId="customers-list-prev-button"
                variant="secondary"
                disabled={params.page <= 1}
                onClick={() => goToPage(params.page - 1)}
              >
                Anterior
              </Button>
              <p
                data-testid="customers-list-page-text"
                className="tabular-nums"
              >
                {`Página ${params.page} de ${lastPage(data.total, data.page_size)}`}
              </p>
              <Button
                testId="customers-list-next-button"
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

/**
 * The last page for a total: `Y = max(1, ceil(total / 20))` of the brief,
 * with the fixed page size of the API.
 */
function lastPage(total: number, pageSize: number): number {
  return Math.max(1, Math.ceil(total / pageSize));
}

export default function CustomersPage() {
  useDocumentTitle("Clientes");

  return (
    <Suspense
      fallback={
        <p
          role="status"
          data-testid="customers-list-loading-status"
          aria-busy="true"
        >
          Cargando…
        </p>
      }
    >
      <CustomersListContent />
    </Suspense>
  );
}
