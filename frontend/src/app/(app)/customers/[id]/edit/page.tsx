"use client";

import { Button, Link } from "@/components/ui";
import { useMe } from "@/features/auth/hooks";
import { CustomerForm } from "@/features/customers/CustomerForm";
import { useCustomer } from "@/features/customers/hooks";
import { parseCustomerIdParam } from "@/features/customers/params";
import { canManageCustomers } from "@/features/customers/permissions";
import { ApiRequestError, INTERNAL_ERROR_DETAIL } from "@/lib/api";
import { useParams } from "next/navigation";
import { useState } from "react";

export default function CustomerEditPage() {
  const id = parseCustomerIdParam(useParams().id);

  if (id === null) {
    // Not a valid id: show the not-found alert and the back link without
    // calling the API.
    return (
      <div>
        <p
          role="alert"
          data-testid="customers-form-error-alert"
          tabIndex={-1}
        >
          No se encontró el recurso solicitado.
        </p>
        <Link href="/customers" testId="customers-form-cancel-link">
          Cancelar
        </Link>
      </div>
    );
  }

  return <CustomerEdit id={id} />;
}

function CustomerEdit({ id }: { id: number }) {
  const me = useMe();
  const customer = useCustomer(id);
  // Bumped after "Recargar datos" refetches the customer; the form resets
  // to the server values and captures the new version.
  const [resetSignal, setResetSignal] = useState(0);

  if (me.isPending) {
    return (
      <p
        role="status"
        data-testid="customers-form-loading-status"
        aria-busy="true"
      >
        Cargando…
      </p>
    );
  }

  const user = me.data;
  if (user && !canManageCustomers(user.role)) {
    return (
      <p
        role="alert"
        data-testid="customers-form-forbidden-alert"
      >
        No tienes permiso para realizar esta acción.
      </p>
    );
  }

  if (customer.isPending) {
    return (
      <p
        role="status"
        data-testid="customers-form-loading-status"
        aria-busy="true"
      >
        Cargando…
      </p>
    );
  }

  if (customer.isError) {
    const is404 = customer.error instanceof ApiRequestError
      && customer.error.problem.status === 404;
    const detail = customer.error instanceof ApiRequestError
      ? customer.error.problem.detail
      : INTERNAL_ERROR_DETAIL;

    return (
      <div>
        <p
          role="alert"
          data-testid="customers-form-error-alert"
          tabIndex={-1}
        >
          {detail}
        </p>
        {is404 ? null : (
          <Button
            testId="customers-form-retry-button"
            onClick={() => void customer.refetch()}
          >
            Reintentar
          </Button>
        )}
      </div>
    );
  }

  async function handleReload() {
    await customer.refetch();
    setResetSignal((signal) => signal + 1);
  }

  return (
    <CustomerForm
      mode="edit"
      customer={customer.data}
      resetSignal={resetSignal}
      onReload={handleReload}
    />
  );
}
