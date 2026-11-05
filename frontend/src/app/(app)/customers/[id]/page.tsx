"use client";

import { Button, Link } from "@/components/ui";
import { useMe } from "@/features/auth/hooks";
import {
  useCustomer,
  useSetCustomerStatus,
} from "@/features/customers/hooks";
import { parseCustomerIdParam } from "@/features/customers/params";
import { canManageCustomers } from "@/features/customers/permissions";
import { statusLabel } from "@/features/customers/types";
import { ApiRequestError, INTERNAL_ERROR_DETAIL } from "@/lib/api";
import { useParams } from "next/navigation";
import { useRef, useState } from "react";

export default function CustomerDetailPage() {
  const id = parseCustomerIdParam(useParams().id);

  if (id === null) {
    // Not a valid id: show the not-found alert and the back link without
    // calling the API.
    return (
      <div>
        <p role="alert" data-testid="customers-detail-error-alert">
          No se encontró el recurso solicitado.
        </p>
        <Link href="/customers" testId="customers-detail-back-link">
          Volver a clientes
        </Link>
      </div>
    );
  }

  return <CustomerDetail id={id} />;
}

function CustomerDetail({ id }: { id: number }) {
  const me = useMe();
  const customer = useCustomer(id);
  const statusMutation = useSetCustomerStatus();

  const [actionError, setActionError] = useState<string | null>(null);
  // The busy guard lives in the handler: a state update would not be
  // visible to a second click processed in the same tick.
  const busyRef = useRef(false);
  const [busy, setBusy] = useState(false);

  if (customer.isPending) {
    return (
      <p
        role="status"
        data-testid="customers-detail-loading-status"
        aria-busy="true"
      >
        Cargando…
      </p>
    );
  }

  if (customer.isError) {
    const problem = customer.error instanceof ApiRequestError
      ? customer.error.problem
      : { status: 0, detail: INTERNAL_ERROR_DETAIL };
    const is404 = problem.status === 404;

    return (
      <div>
        <p role="alert" data-testid="customers-detail-error-alert">
          {problem.detail}
        </p>
        {is404 ? (
          <Link href="/customers" testId="customers-detail-back-link">
            Volver a clientes
          </Link>
        ) : (
          <Button
            testId="customers-detail-retry-button"
            onClick={() => void customer.refetch()}
          >
            Reintentar
          </Button>
        )}
      </div>
    );
  }

  const data = customer.data;
  const user = me.data;
  const canManage = user ? canManageCustomers(user.role) : false;

  async function handleStatusChange() {
    if (busyRef.current || statusMutation.isPending) {
      return;
    }
    busyRef.current = true;
    setBusy(true);
    setActionError(null);
    try {
      await statusMutation.mutateAsync({
        id: data.id,
        action: data.status === "active" ? "deactivate" : "reactivate",
        version: data.version,
      });
    } catch (error) {
      setActionError(
        error instanceof ApiRequestError
          ? error.problem.detail
          : INTERNAL_ERROR_DETAIL,
      );
      // After any failed status change refetch the customer, so the next
      // click sends the fresh version instead of repeating the stale one.
      await customer.refetch();
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }

  return (
    <div>
      <h1 data-testid="customers-detail-heading">{data.name}</h1>

      {actionError ? (
        <p role="alert" data-testid="customers-detail-alert">
          {actionError}
        </p>
      ) : null}

      <dl>
        <div>
          <dt>Nombre</dt>
          <dd data-testid="customers-detail-name-text">{data.name}</dd>
        </div>
        <div>
          <dt>Email</dt>
          <dd data-testid="customers-detail-email-text">{data.email}</dd>
        </div>
        <div>
          <dt>Teléfono</dt>
          <dd data-testid="customers-detail-phone-text">
            {data.phone ?? "—"}
          </dd>
        </div>
        <div>
          <dt>ID fiscal</dt>
          <dd data-testid="customers-detail-taxid-text">
            {data.tax_id ?? "—"}
          </dd>
        </div>
        <div>
          <dt>Dirección</dt>
          <dd data-testid="customers-detail-address-text">
            {data.address ?? "—"}
          </dd>
        </div>
        <div>
          <dt>Estado</dt>
          <dd data-testid="customers-detail-state-status">
            {statusLabel(data.status)}
          </dd>
        </div>
      </dl>

      {canManage ? (
        <div>
          <Link
            href={`/customers/${data.id}/edit`}
            testId="customers-detail-edit-link"
          >
            Editar
          </Link>
          <Button
            testId={
              data.status === "active"
                ? "customers-detail-deactivate-button"
                : "customers-detail-reactivate-button"
            }
            loading={busy}
            onClick={() => void handleStatusChange()}
          >
            {data.status === "active" ? "Desactivar" : "Reactivar"}
          </Button>
        </div>
      ) : null}

      <Link href="/customers" testId="customers-detail-back-link">
        Volver a clientes
      </Link>
    </div>
  );
}
