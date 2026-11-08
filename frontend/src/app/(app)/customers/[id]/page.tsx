"use client";

import { Alert, Button, ConfirmDialog, Link } from "@/components/ui";
import { useMe } from "@/features/auth/hooks";
import {
  useCustomer,
  useSetCustomerStatus,
} from "@/features/customers/hooks";
import { parseCustomerIdParam } from "@/features/customers/params";
import { canManageCustomers } from "@/features/customers/permissions";
import { statusLabel } from "@/features/customers/types";
import { canEditOrders } from "@/features/orders/permissions";
import { ApiRequestError, INTERNAL_ERROR_DETAIL } from "@/lib/api";
import { useDocumentTitle } from "@/lib/useDocumentTitle";
import { useParams } from "next/navigation";
import { useRef, useState } from "react";

const BADGE_CLASSES = "inline-flex rounded-sm px-2 py-0.5 text-xs font-semibold";

/** The definition row of the detail card: label in muted, value in ink. */
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

export default function CustomerDetailPage() {
  // The section title covers the invalid-id screen too; the content
  // component replaces it with the customer's name once it arrives.
  useDocumentTitle("Clientes");
  const id = parseCustomerIdParam(useParams().id);

  if (id === null) {
    // Not a valid id: show the not-found alert and the back link without
    // calling the API.
    return (
      <div>
        <Alert testId="customers-detail-error-alert">
          No se encontró el recurso solicitado.
        </Alert>
        <div className="mt-3">
          <Link href="/customers" testId="customers-detail-back-link">
            Volver a clientes
          </Link>
        </div>
      </div>
    );
  }

  return <CustomerDetail id={id} />;
}

function CustomerDetail({ id }: { id: number }) {
  const me = useMe();
  const customer = useCustomer(id);
  const statusMutation = useSetCustomerStatus();

  // The tab: the section while the record is in the air (and while a
  // failed request is on screen), the name after it arrives.
  useDocumentTitle(
    customer.isSuccess ? `Cliente ${customer.data.name}` : "Clientes",
  );

  const [actionError, setActionError] = useState<string | null>(null);
  // The busy guard lives in the handler: a state update would not be
  // visible to a second click processed in the same tick.
  const busyRef = useRef(false);
  const [busy, setBusy] = useState(false);
  /** Which action is running; the dialog of the deactivate reads it. */
  const [statusAction, setStatusAction] = useState<
    "deactivate" | "reactivate" | null
  >(null);
  // The confirmation of the destructive deactivate (the dialog below).
  const [deactivateDialogOpen, setDeactivateDialogOpen] = useState(false);

  if (customer.isPending) {
    return (
      <p
        role="status"
        data-testid="customers-detail-loading-status"
        aria-busy="true"
        className="text-muted"
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
        <Alert testId="customers-detail-error-alert">
          {problem.detail}
        </Alert>
        <div className="mt-3">
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
      </div>
    );
  }

  const data = customer.data;
  const user = me.data;
  const canManage = user ? canManageCustomers(user.role) : false;
  // The permission of the "Nuevo pedido" shortcut: the same one the
  // create-order screen checks (docs/SPEC.md section 5), and only for a
  // customer that can still receive one (docs/SPEC.md section 4). It is
  // independent of the customer-management permission: the roles only
  // happen to coincide today.
  const canCreateOrder = user
    ? canEditOrders(user.role) && data.status === "active"
    : false;

  async function handleStatusChange(
    action: "deactivate" | "reactivate",
  ): Promise<void> {
    if (busyRef.current || statusMutation.isPending) {
      return;
    }
    busyRef.current = true;
    setBusy(true);
    setStatusAction(action);
    setActionError(null);
    try {
      await statusMutation.mutateAsync({
        id: data.id,
        action,
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
      setStatusAction(null);
      // The confirmation dialog of the deactivate closes when the
      // request ends, failure or success: the answer is on screen.
      if (action === "deactivate") {
        setDeactivateDialogOpen(false);
      }
    }
  }

  return (
    <div>
      <h1 data-testid="customers-detail-heading">{data.name}</h1>

      {actionError ? (
        <div className="mt-3">
          <Alert testId="customers-detail-alert">
            {actionError}
          </Alert>
        </div>
      ) : null}

      <div className="mt-6 rounded-lg border border-line bg-surface p-5">
        <dl className="flex flex-col gap-3">
          <DetailRow label="Nombre">
            <dd data-testid="customers-detail-name-text" className="break-words">
              {data.name}
            </dd>
          </DetailRow>
          <DetailRow label="Email">
            <dd data-testid="customers-detail-email-text" className="break-words">
              {data.email}
            </dd>
          </DetailRow>
          <DetailRow label="Teléfono">
            <dd data-testid="customers-detail-phone-text" className="break-words tabular-nums">
              {data.phone ?? <span className="text-muted">—</span>}
            </dd>
          </DetailRow>
          <DetailRow label="ID fiscal">
            <dd data-testid="customers-detail-taxid-text" className="break-words tabular-nums">
              {data.tax_id ?? <span className="text-muted">—</span>}
            </dd>
          </DetailRow>
          <DetailRow label="Dirección">
            <dd data-testid="customers-detail-address-text" className="break-words">
              {data.address ?? <span className="text-muted">—</span>}
            </dd>
          </DetailRow>
          <DetailRow label="Estado">
            <dd data-testid="customers-detail-state-status">
              <span
                className={[
                  BADGE_CLASSES,
                  data.status === "active"
                    ? "bg-ok-bg text-accent"
                    : "bg-off-bg text-muted",
                ].join(" ")}
              >
                {statusLabel(data.status)}
              </span>
            </dd>
          </DetailRow>
        </dl>
      </div>

      {/*
       * The section that connects the two modules: from here the orders
       * of this customer are one link away (docs/SPEC.md section 5, the
       * `customer_id` filter of the orders list). Visible to every role,
       * for active and inactive customers alike.
       */}
      <section className="mt-6">
        <h2 data-testid="customers-detail-orders-heading">Pedidos</h2>
        <div className="mt-2">
          <Link
            href={`/orders?customer_id=${data.id}`}
            testId="customers-detail-orders-link"
          >
            Ver pedidos de este cliente
          </Link>
        </div>
      </section>

      {canManage || canCreateOrder ? (
        <div className="mt-6 flex flex-wrap items-center gap-3">
          {canCreateOrder ? (
            /*
             * The shortcut of task 039: the new-order form with this
             * customer already chosen (`/orders/new` reads
             * `customer_id`). Only for an active customer and a user who
             * can edit draft orders; the server stays the authority.
             */
            <Link
              href={`/orders/new?customer_id=${data.id}`}
              testId="customers-detail-neworder-link"
              variant="secondary"
            >
              Nuevo pedido
            </Link>
          ) : null}
          {canManage ? (
            <>
              <Link
                href={`/customers/${data.id}/edit`}
                testId="customers-detail-edit-link"
                variant="secondary"
              >
                Editar
              </Link>
              {data.status === "active" ? (
                <Button
                  testId="customers-detail-deactivate-button"
                  variant="secondary"
                  onClick={() => setDeactivateDialogOpen(true)}
                >
                  Desactivar
                </Button>
              ) : (
                <Button
                  testId="customers-detail-reactivate-button"
                  variant="secondary"
                  loading={busy}
                  onClick={() => void handleStatusChange("reactivate")}
                >
                  Reactivar
                </Button>
              )}
            </>
          ) : null}
        </div>
      ) : null}

      {/*
       * The confirmation of the destructive deactivate: the request runs
       * only after "Sí, desactivar", with the same error handling; the
       * reactivation is not destructive and stays immediate above.
       */}
      <ConfirmDialog
        open={deactivateDialogOpen}
        title={`¿Desactivar a ${data.name}?`}
        titleId="customers-deactivate-title"
        messageId="customers-deactivate-message"
        testId="customers-deactivate-confirm-dialog"
        titleTestId="customers-deactivate-title-heading"
        messageTestId="customers-deactivate-message-text"
        confirmTestId="customers-deactivate-confirm-button"
        cancelTestId="customers-deactivate-back-button"
        confirmLabel="Sí, desactivar"
        pending={busy && statusAction === "deactivate"}
        onConfirm={() => void handleStatusChange("deactivate")}
        onCancel={() => setDeactivateDialogOpen(false)}
      >
        No podrá recibir pedidos nuevos. Sus pedidos y facturas existentes
        no cambian.
      </ConfirmDialog>

      <div className="mt-6">
        <Link href="/customers" testId="customers-detail-back-link">
          Volver a clientes
        </Link>
      </div>
    </div>
  );
}
