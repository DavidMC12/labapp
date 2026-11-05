"use client";

import { Alert } from "@/components/ui";
import { Button, Link } from "@/components/ui";
import { useLogout, useMe } from "@/features/auth/hooks";
import { roleLabel } from "@/features/auth/types";
import { ApiRequestError, INTERNAL_ERROR_DETAIL } from "@/lib/api";
import type { TestId } from "@/lib/testid";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

/** A section link covers the section root and everything under it. */
function isCurrentSection(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

function StrokeIcon({ shapes }: { shapes: React.ReactNode }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 16 16"
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="shrink-0"
    >
      {shapes}
    </svg>
  );
}

function ClientesIcon() {
  return (
    <StrokeIcon shapes={<><circle cx="8" cy="5" r="2.5" /><path d="M2.5 13.5c.9-2.8 2.9-4.2 5.5-4.2s4.6 1.4 5.5 4.2" /></>} />
  );
}

function PedidosIcon() {
  return (
    <StrokeIcon shapes={<><path d="M8 1.5 14 4.5v7L8 14.5 2 11.5v-7Z" /><path d="M2 4.5 8 7.5l6-3" /><path d="M8 7.5v7" /></>} />
  );
}

function FacturasIcon() {
  return (
    <StrokeIcon shapes={<><path d="M4.5 1.5h5l3 3v10a1 1 0 0 1-1 1h-7a1 1 0 0 1-1-1v-12a1 1 0 0 1 1-1Z" /><path d="M9.5 1.5v3h3" /><path d="M6 8h4" /><path d="M6 11h4" /></>} />
  );
}

/** The ledger-page mark of the brand, drawn for this theme. */
function BrandMark() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 16 16"
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="shrink-0"
    >
      <rect x="2" y="2" width="12" height="12" rx="1.5" />
      <path d="M5.5 5.5H11" />
      <path d="M5.5 8H11" />
      <path d="M5.5 10.5H8.5" />
    </svg>
  );
}

export default function AppLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const me = useMe();
  const router = useRouter();
  const logout = useLogout();
  const loggingOutRef = useRef(false);

  const pathname = usePathname();

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
        className="min-h-screen p-4 text-muted"
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
      <div className="min-h-screen p-4">
        <Alert testId="app-shell-error-alert">{problemDetail}</Alert>
        <div className="mt-3">
          <Button
            testId="app-shell-retry-button"
            onClick={() => void me.refetch()}
          >
            Reintentar
          </Button>
        </div>
      </div>
    );
  }

  const user = me.data ?? null;

  if (user === null) {
    // No session: the effect navigates to /login; render nothing user
    // related while that happens.
    return null;
  }

  type NavItem = {
    href: string;
    testId: TestId;
    label: string;
    icon: React.ReactNode;
  };

  const navItems: NavItem[] = [
    {
      href: "/customers",
      testId: "app-nav-customers-link",
      label: "Clientes",
      icon: <ClientesIcon />,
    },
    {
      href: "/orders",
      testId: "app-nav-orders-link",
      label: "Pedidos",
      icon: <PedidosIcon />,
    },
    {
      href: "/invoices",
      testId: "app-nav-invoices-link",
      label: "Facturas",
      icon: <FacturasIcon />,
    },
  ];

  // The rail on 768px and up; a full-width top bar below. The DOM order
  // (brand, navigation, user block with the logout) is the tab order in
  // both layouts; the mobile top bar is a row of the user block under the
  // navigation, never on the brand row.
  return (
    <div className="min-h-screen md:grid md:grid-cols-[212px_minmax(0,1fr)]">
      <aside className="flex flex-col bg-rail text-rail-ink md:sticky md:top-0 md:h-screen">
        <div className="px-4 py-3 md:px-3 md:pt-4">
          <Link
            href="/"
            testId="app-nav-home-link"
            variant="rail"
            className="font-serif text-lg font-semibold text-rail-ink"
          >
            <BrandMark />
            LabApp
          </Link>
        </div>

        <nav
          aria-label="Principal"
          className="flex gap-1 overflow-x-auto p-1.5 md:mt-4 md:flex-col md:px-3"
        >
          {navItems.map((item) => {
            const current = isCurrentSection(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                testId={item.testId}
                variant="rail"
                aria-current={current ? "page" : undefined}
                className={[
                  "whitespace-nowrap",
                  current
                    ? "bg-paper font-semibold text-ink"
                    : "text-rail-muted",
                ].join(" ")}
              >
                {item.icon}
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-3 px-4 pb-2 md:mt-auto md:flex-col md:items-stretch md:border-t md:border-rail-muted/40 md:px-3 md:py-3">
          <p
            data-testid="app-user-name-text"
            className="text-[15px] font-medium"
          >
            {user.name}
          </p>
          <p
            data-testid="app-user-role-text"
            className="text-[13px] text-rail-muted"
          >
            {roleLabel(user.role)}
          </p>
          <Button
            testId="app-logout-button"
            variant="rail"
            className="ml-auto md:ml-0 md:w-full"
            loading={logout.isPending}
            onClick={() => void handleLogout()}
          >
            Salir
          </Button>
        </div>
      </aside>

      <main className="min-w-0 flex-1 px-4 py-6 md:px-6">{children}</main>
    </div>
  );
}
