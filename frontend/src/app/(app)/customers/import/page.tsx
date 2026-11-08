"use client";

import { Alert } from "@/components/ui";
import { useMe } from "@/features/auth/hooks";
import { CustomersImportForm } from "@/features/customers/ImportForm";
import { canManageCustomers } from "@/features/customers/permissions";
import { useDocumentTitle } from "@/lib/useDocumentTitle";

/**
 * The customers import page. Reading the session from the shell cache;
 * the import form is only offered to the roles that can manage customers
 * (Admin and Sales), and the server remains the authority.
 */
export default function CustomerImportPage() {
  useDocumentTitle("Importar clientes");
  const me = useMe();

  if (me.isPending) {
    return (
      <p
        role="status"
        data-testid="customers-import-loading-status"
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
      <Alert testId="customers-import-forbidden-alert">
        No tienes permiso para realizar esta acción.
      </Alert>
    );
  }

  return <CustomersImportForm />;
}
