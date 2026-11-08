"use client";

import { Alert, Button, Input, Link, Select, TableScroll } from "@/components/ui";
import { useMe } from "@/features/auth/hooks";
import { useCustomers } from "@/features/customers/hooks";
import { parseCustomerListParams } from "@/features/customers/params";
import { canManageCustomers } from "@/features/customers/permissions";
import { statusLabel } from "@/features/customers/types";
import { ApiRequestError, INTERNAL_ERROR_DETAIL } from "@/lib/api";
import { useDocumentTitle } from "@/lib/useDocumentTitle";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

/**
 * The list URL of the screen: page (always) plus the search values that
 * have one. This is what every navigation writes, so links can be shared.
 */
function listUrl(page: number, q: string | null, status: string | null): string {
  const search = new URLSearchParams();
  search.set("page", String(page));
  if (q) {
    search.set("q", q);
  }
  if (status) {
    search.set("status", status);
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
  const list = useCustomers({
    page: params.page,
    q: params.q ?? undefined,
    status: params.status ?? undefined,
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
    router.replace(listUrl(last, params.q, params.status));
  }, [data, params.page, params.q, params.status, router]);

  function handleSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // Submitting goes back to page 1 with the trimmed values.
    router.push(listUrl(1, qInput.trim() || null, statusInput || null));
  }

  function goToPage(page: number) {
    router.push(listUrl(page, params.q, params.status));
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
          <Link href="/customers/new" testId="customers-list-new-link" variant="primary">
            Nuevo cliente
          </Link>
        ) : null}
      </div>

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
           * The wide content scrolls inside this wrapper, never the page:
           * the padding keeps the 3px focus ring visible around the
           * scrollbar edges.
           */}
          <TableScroll testId="customers-list-scroll-region" label="Tabla de clientes" className="mt-6">
            <table
              data-testid="customers-list-table"
              className="min-w-[40rem]"
            >
              <thead>
                <tr>
                  <th scope="col" className={TABLE_HEAD_CLASSES}>Nombre</th>
                  <th scope="col" className={TABLE_HEAD_CLASSES}>Email</th>
                  <th scope="col" className={TABLE_HEAD_CLASSES}>ID fiscal</th>
                  <th scope="col" className={TABLE_HEAD_CLASSES}>Estado</th>
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
