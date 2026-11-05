"use client";

import { Button, Input, Link, Select } from "@/components/ui";
import { useMe } from "@/features/auth/hooks";
import { useCustomers } from "@/features/customers/hooks";
import { parseCustomerListParams } from "@/features/customers/params";
import { canManageCustomers } from "@/features/customers/permissions";
import { statusLabel } from "@/features/customers/types";
import { ApiRequestError, INTERNAL_ERROR_DETAIL } from "@/lib/api";
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
      <h1 data-testid="customers-list-heading">Clientes</h1>

      {canManage ? (
        <Link href="/customers/new" testId="customers-list-new-link">
          Nuevo cliente
        </Link>
      ) : null}

      <form
        data-testid="customers-list-search-form"
        onSubmit={handleSearch}
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
        <Button testId="customers-list-search-button" type="submit">
          Buscar
        </Button>
      </form>

      {list.isPending ? (
        <p
          role="status"
          data-testid="customers-list-loading-status"
          aria-busy="true"
        >
          Cargando…
        </p>
      ) : list.isError ? (
        <div>
          <p role="alert" data-testid="customers-list-error-alert">
            {problemDetail()}
          </p>
          <Button
            testId="customers-list-retry-button"
            onClick={() => void list.refetch()}
          >
            Reintentar
          </Button>
        </div>
      ) : data !== null && data.items.length === 0 ? (
        <p role="status" data-testid="customers-list-empty-status">
          No hay clientes que coincidan.
        </p>
      ) : data !== null ? (
        <>
          <table data-testid="customers-list-table">
            <thead>
              <tr>
                <th scope="col">Nombre</th>
                <th scope="col">Email</th>
                <th scope="col">ID fiscal</th>
                <th scope="col">Estado</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((customer) => (
                <tr
                  key={customer.id}
                  data-testid={`customers-list-row-${customer.id}`}
                >
                  <td data-testid={`customers-list-name-cell-${customer.id}`}>
                    <Link
                      href={`/customers/${customer.id}`}
                      testId={`customers-list-view-link-${customer.id}`}
                    >
                      {customer.name}
                    </Link>
                  </td>
                  <td data-testid={`customers-list-email-cell-${customer.id}`}>
                    {customer.email}
                  </td>
                  <td data-testid={`customers-list-taxid-cell-${customer.id}`}>
                    {customer.tax_id ?? "—"}
                  </td>
                  <td data-testid={`customers-list-state-cell-${customer.id}`}>
                    {statusLabel(customer.status)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <nav aria-label="Paginación de clientes">
            <Button
              testId="customers-list-prev-button"
              disabled={params.page <= 1}
              onClick={() => goToPage(params.page - 1)}
            >
              Anterior
            </Button>
            <Button
              testId="customers-list-next-button"
              disabled={params.page >= lastPage(data.total, data.page_size)}
              onClick={() => goToPage(params.page + 1)}
            >
              Siguiente
            </Button>
            <p data-testid="customers-list-page-text">
              {`Página ${params.page} de ${lastPage(data.total, data.page_size)}`}
            </p>
            <p data-testid="customers-list-total-text">
              {data.total === 1 ? "1 cliente" : `${data.total} clientes`}
            </p>
          </nav>
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
