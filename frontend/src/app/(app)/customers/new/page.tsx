"use client";

import { Alert } from "@/components/ui";
import { useMe } from "@/features/auth/hooks";
import { CustomerForm } from "@/features/customers/CustomerForm";
import { canManageCustomers } from "@/features/customers/permissions";

/**
 * The create customer page. Reading the session from the shell cache; the
 * create form is only offered to the roles that can manage customers, and
 * the server remains the authority.
 */
export default function CustomerNewPage() {
  const me = useMe();

  if (me.isPending) {
    return (
      <p
        role="status"
        data-testid="customers-form-loading-status"
        aria-busy="true"
        className="text-muted"
      >
        Cargando…
      </p>
    );
  }

  const user = me.data;
  if (user && !canManageCustomers(user.role)) {
    return (
      <Alert testId="customers-form-forbidden-alert">
        No tienes permiso para realizar esta acción.
      </Alert>
    );
  }

  return <CustomerForm mode="create" />;
}
