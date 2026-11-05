"use client";

import { Alert, Button, Input, Link, Select } from "@/components/ui";
import { useMe } from "@/features/auth/hooks";
import { useOrders } from "@/features/orders/hooks";
import { parseOrderListParams } from "@/features/orders/params";
import { canEditOrders } from "@/features/orders/permissions";
import { orderStatusLabel } from "@/features/orders/types";
import { ApiRequestError, INTERNAL_ERROR_DETAIL } from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/format";
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
  return `/orders?${search.toString()}`;
}

/** The classes of a ledger header cell and a ledger body cell. */
const TABLE_HEAD_CLASSES = [
  "border-b-2 border-ink px-[10px] py-[9px] text-left",
  "text-xs font-medium uppercase tracking-[0.07em] text-muted",
].join(" ");

const TABLE_CELL_CLASSES = [
  "border-b border-line px-[10px] py-[9px] text-ink tabular-nums",
].join(" ");

const STATE_BADGE_CLASSES = [
  "inline-flex rounded-sm px-2 py-0.5 text-xs font-semibold",
  // Confirmed, paid and shipped orders are the "positive" shades of the
  // theme; drafts and cancelled ones stay quiet.
  "bg-ok-bg text-accent",
].join(" ");

const STATE_MUTED_BADGE_CLASSES = [
  "inline-flex rounded-sm px-2 py-0.5 text-xs font-semibold",
  "bg-off-bg text-muted",
].join(" ");

function badgeClasses(status: string): string {
  return status === "cancelled" || status === "draft"
    ? STATE_MUTED_BADGE_CLASSES
    : STATE_BADGE_CLASSES;
}

function OrdersListContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const me = useMe();

  const params = parseOrderListParams(searchParams);
  const list = useOrders({
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
  const canEdit = user ? canEditOrders(user.role) : false;

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 data-testid="orders-list-heading">Pedidos</h1>

        {canEdit ? (
          <Link href="/orders/new" testId="orders-list-new-link" variant="primary">
            Nuevo pedido
          </Link>
        ) : null}
      </div>

      <form
        data-testid="orders-list-search-form"
        onSubmit={handleSearch}
        className="mt-4 grid items-end gap-3 md:grid-cols-[minmax(0,1fr)_minmax(140px,220px)_auto]"
      >
        <Input
          id="orders-list-search"
          testId="orders-list-search-input"
          label="Buscar"
          placeholder="Número o cliente"
          value={qInput}
          onChange={(event) => setQInput(event.target.value)}
        />
        <Select
          id="orders-list-status"
          testId="orders-list-status-select"
          label="Estado"
          value={statusInput}
          onChange={(event) => setStatusInput(event.target.value)}
        >
          <option value="">Todos</option>
          <option value="draft">Borrador</option>
          <option value="confirmed">Confirmado</option>
          <option value="paid">Pagado</option>
          <option value="shipped">Enviado</option>
          <option value="cancelled">Cancelado</option>
        </Select>
        <Button
          testId="orders-list-search-button"
          type="submit"
          variant="secondary"
        >
          Buscar
        </Button>
      </form>

      {list.isPending ? (
        <p
          role="status"
          data-testid="orders-list-loading-status"
          aria-busy="true"
          className="mt-6 text-muted"
        >
          Cargando…
        </p>
      ) : list.isError ? (
        <div className="mt-6">
          <Alert testId="orders-list-error-alert">
            {problemDetail()}
          </Alert>
          <div className="mt-3">
            <Button
              testId="orders-list-retry-button"
              onClick={() => void list.refetch()}
            >
              Reintentar
            </Button>
          </div>
        </div>
      ) : data !== null && data.items.length === 0 ? (
        <p
          role="status"
          data-testid="orders-list-empty-status"
          className="mt-6 text-muted"
        >
          No hay pedidos que coincidan.
        </p>
      ) : data !== null ? (
        <>
          {/*
           * The wide content scrolls inside this wrapper, never the page:
           * the padding keeps the 3px focus ring visible around the
           * scrollbar edges.
           */}
          <div className="mt-6 overflow-x-auto p-1.5">
            <table
              data-testid="orders-list-table"
              className="min-w-[44rem] w-full"
            >
              <thead>
                <tr>
                  <th scope="col" className={TABLE_HEAD_CLASSES}>Número</th>
                  <th scope="col" className={TABLE_HEAD_CLASSES}>Cliente</th>
                  <th scope="col" className={TABLE_HEAD_CLASSES}>Estado</th>
                  <th scope="col" className={TABLE_HEAD_CLASSES}>Líneas</th>
                  <th scope="col" className={TABLE_HEAD_CLASSES}>Total</th>
                  <th scope="col" className={TABLE_HEAD_CLASSES}>Creado</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((order) => (
                  <tr
                    key={order.id}
                    data-testid={`orders-list-row-${order.id}`}
                    className="ledger-row"
                  >
                    <td
                      data-testid={`orders-list-number-cell-${order.id}`}
                      className={TABLE_CELL_CLASSES}
                    >
                      <Link
                        href={`/orders/${order.id}`}
                        testId={`orders-list-view-link-${order.id}`}
                        className="font-medium"
                      >
                        {order.number}
                      </Link>
                    </td>
                    <td
                      data-testid={`orders-list-customer-cell-${order.id}`}
                      className={TABLE_CELL_CLASSES}
                    >
                      {order.customer_name}
                    </td>
                    <td
                      data-testid={`orders-list-state-cell-${order.id}`}
                      className={`${TABLE_CELL_CLASSES} whitespace-nowrap`}
                    >
                      <span className={badgeClasses(order.status)}>
                        {orderStatusLabel(order.status)}
                      </span>
                    </td>
                    <td
                      data-testid={`orders-list-lines-cell-${order.id}`}
                      className={TABLE_CELL_CLASSES}
                    >
                      {order.line_count}
                    </td>
                    <td
                      data-testid={`orders-list-total-cell-${order.id}`}
                      className={`${TABLE_CELL_CLASSES} whitespace-nowrap text-right`}
                    >
                      {formatMoney(order.total)}
                    </td>
                    <td
                      data-testid={`orders-list-created-cell-${order.id}`}
                      className={`${TABLE_CELL_CLASSES} whitespace-nowrap`}
                    >
                      {formatDate(order.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/*
           * The ledger footer, matching the customers list: a 4px double
           * rule of ink above it, the total on the left and the
           * pagination nav on the right.
           */}
          <div
            data-testid="orders-list-footer-item"
            className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t-4 border-double border-ink pt-3"
          >
            <p
              data-testid="orders-list-total-text"
              className="font-semibold tabular-nums"
            >
              {data.total === 1 ? "1 pedido" : `${data.total} pedidos`}
            </p>
            <nav
              aria-label="Paginación de pedidos"
              className="flex flex-wrap items-center gap-3"
            >
              <Button
                testId="orders-list-prev-button"
                variant="secondary"
                disabled={params.page <= 1}
                onClick={() => goToPage(params.page - 1)}
              >
                Anterior
              </Button>
              <p
                data-testid="orders-list-page-text"
                className="tabular-nums"
              >
                {`Página ${params.page} de ${lastPage(data.total, data.page_size)}`}
              </p>
              <Button
                testId="orders-list-next-button"
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
 * The last page for a total: `Y = max(1, ceil(total / 20))`, with the
 * fixed page size of the API.
 */
function lastPage(total: number, pageSize: number): number {
  return Math.max(1, Math.ceil(total / pageSize));
}

export default function OrdersPage() {
  return (
    <Suspense
      fallback={
        <p
          role="status"
          data-testid="orders-list-loading-status"
          aria-busy="true"
        >
          Cargando…
        </p>
      }
    >
      <OrdersListContent />
    </Suspense>
  );
}
