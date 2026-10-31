"use client";

import { Button, Link } from "@/components/ui";
import { useLogout, useMe } from "@/features/auth/hooks";
import { roleLabel } from "@/features/auth/types";
import { ApiRequestError, INTERNAL_ERROR_DETAIL } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

export default function AppLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const me = useMe();
  const router = useRouter();
  const logout = useLogout();
  const loggingOutRef = useRef(false);

  // No session: an expired or missing session redirects silently for now.
  useEffect(() => {
    if (me.isSuccess && me.data === null) {
      router.replace("/login");
    }
  }, [me.isSuccess, me.data, router]);

  async function handleLogout() {
    // The guard lives in the handler: state updates arrive too late for a
    // second click processed in the same tick.
    if (loggingOutRef.current || logout.isPending) {
      return;
    }
    loggingOutRef.current = true;
    try {
      await logout.mutateAsync();
    } catch {
      // Whatever the answer, the hook already cleared the cache; the
      // rejection is not actionable and is swallowed on purpose.
    } finally {
      loggingOutRef.current = false;
      router.replace("/login");
    }
  }

  if (me.isPending) {
    return (
      <p
        role="status"
        data-testid="app-shell-loading-status"
        aria-busy="true"
      >
        Cargando…
      </p>
    );
  }

  // Every error other than a 401 (which useMe resolves to null) goes to
  // the error branch: an ApiRequestError shows its detail, anything else
  // shows the INTERNAL_ERROR text.
  const isSilent401 =
    me.error instanceof ApiRequestError && me.error.problem.status === 401;

  if (me.isError && !isSilent401) {
    const problemDetail: string =
      me.error instanceof ApiRequestError
        ? me.error.problem.detail
        : INTERNAL_ERROR_DETAIL;

    return (
      <div>
        <p role="alert" data-testid="app-shell-error-alert">
          {problemDetail}
        </p>
        <Button
          testId="app-shell-retry-button"
          onClick={() => void me.refetch()}
        >
          Reintentar
        </Button>
      </div>
    );
  }

  const user = me.data ?? null;

  if (user === null) {
    // No session: the effect navigates to /login; render nothing user
    // related while that happens.
    return null;
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-gray-200">
        <div className="flex items-center gap-4 px-4 py-3">
          <Link href="/" testId="app-nav-home-link">
            LabApp
          </Link>
          <nav aria-label="Principal" className="flex items-center gap-4">
            <Link href="/customers" testId="app-nav-customers-link">
              Clientes
            </Link>
            <Link href="/orders" testId="app-nav-orders-link">
              Pedidos
            </Link>
            <Link href="/invoices" testId="app-nav-invoices-link">
              Facturas
            </Link>
          </nav>
          <div className="ml-auto flex items-center gap-4">
            <p data-testid="app-user-name-text">{user.name}</p>
            <p data-testid="app-user-role-text">{roleLabel(user.role)}</p>
            <Button
              testId="app-logout-button"
              loading={logout.isPending}
              onClick={() => void handleLogout()}
            >
              Salir
            </Button>
          </div>
        </div>
      </header>
      <main className="flex-1 px-4 py-6">{children}</main>
    </div>
  );
}
