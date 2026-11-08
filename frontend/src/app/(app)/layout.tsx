"use client";

import { Alert } from "@/components/ui";
import { Button, Link, ThemeSelect } from "@/components/ui";
import { LedgerMark } from "@/components/LedgerMark";
import { useLogout, useMe } from "@/features/auth/hooks";
import { SESSION_EXPIRED_QUERY_KEY } from "@/features/auth/session";
import { roleLabel } from "@/features/auth/types";
import { ApiRequestError, INTERNAL_ERROR_DETAIL } from "@/lib/api";
import type { TestId } from "@/lib/testid";
import { usePathname, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
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

function ProductosIcon() {
  return (
    <StrokeIcon shapes={<><path d="M2.5 5h11v8.5h-11Z" /><path d="M4.5 2.5V5M8 2.5V5M11.5 2.5V5" /><path d="M2.5 8h11" /></>} />
  );
}

function ConfiguracionIcon() {
  return (
    <StrokeIcon shapes={<><circle cx="8" cy="8" r="2.5" /><path d="M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M12.6 3.4l-1.4 1.4M4.8 11.2l-1.4 1.4" /></>} />
  );
}

export default function AppLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const me = useMe();
  const queryClient = useQueryClient();
  const router = useRouter();
  const logout = useLogout();
  const loggingOutRef = useRef(false);

  // The current section link of the phone navigation row (task 038): the
  // row scrolls horizontally, so the section the user navigated to is
  // scrolled into view.
  const currentLinkRef = useRef<HTMLAnchorElement | null>(null);

  const pathname = usePathname();

  // No session: the redirect says why. A 401 SESSION_EXPIRED left the flag
  // under SESSION_EXPIRED_QUERY_KEY (see noteUnauthorized), so the user
  // gets /login?expired=1 and the login page shows the notice; any other
  // way of losing the session goes to /login exactly as before.
  useEffect(() => {
    if (me.isSuccess && me.data === null) {
      const expired =
        queryClient.getQueryData(SESSION_EXPIRED_QUERY_KEY) === true;
      router.replace(expired ? "/login?expired=1" : "/login");
    }
  }, [me.isSuccess, me.data, queryClient, router]);

  // Keep the current navigation link visible on the phone: the single
  // scrollable row moves to the section that just came into view. A no-op
  // on the home (no link is current) and on the desktop rail (never
  // overflows).
  useEffect(() => {
    currentLinkRef.current?.scrollIntoView({
      inline: "nearest",
      block: "nearest",
    });
  }, [pathname]);

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
      href: "/products",
      testId: "app-nav-products-link",
      label: "Productos",
      icon: <ProductosIcon />,
    },
    {
      href: "/invoices",
      testId: "app-nav-invoices-link",
      label: "Facturas",
      icon: <FacturasIcon />,
    },
    {
      href: "/settings",
      testId: "app-nav-settings-link",
      label: "Configuración",
      icon: <ConfiguracionIcon />,
    },
  ];

  // The rail on 768px and up; a full-width top bar below. The DOM order
  // (skip link, brand, navigation, user block with the logout) is the tab
  // order in both layouts; the mobile top bar is a row of the user block
  // under the navigation, never on the brand row.
  return (
    <>
      {/*
       * The first focusable element of the page (WCAG 2.4.1 bypass
       * blocks): hidden until it receives focus, then a solid chip over
       * the paper background. It jumps to the main landmark below.
       */}
      <a
        href="#main-content"
        data-testid="app-skip-link"
        className={[
          "sr-only focus:not-sr-only",
          "focus:fixed focus:left-2 focus:top-2 focus:z-50",
          "focus:rounded-md focus:bg-surface focus:px-3 focus:py-2",
          "focus:font-medium focus:text-ink",
        ].join(" ")}
      >
        Saltar al contenido
      </a>
      <div className="min-h-screen md:grid md:grid-cols-[212px_minmax(0,1fr)]">
        <aside className="flex flex-col bg-rail text-rail-ink md:sticky md:top-0 md:h-screen">
          {/* On the phone the brand row loses the vertical padding of the
            * rail (task 038): py-2 and the desktop padding restored at md. */}
          <div className="px-4 py-2 md:px-3 md:pt-4 md:pb-3">
            <Link
              href="/"
              testId="app-nav-home-link"
              variant="rail"
              className="font-serif text-lg font-semibold text-rail-ink"
            >
              <LedgerMark />
              LabApp
            </Link>
          </div>

          {/*
           * Below 768px the navigation is one row that scrolls
           * horizontally in its own container (task 038): no wrap, the
           * current link held by `scrollIntoView`, and a fade over the
           * right edge (the rail token) as the visible affordance, over
           * the partially cut last link. From md up the rail keeps its
           * wrapped column; the fade disappears.
           */}
          <div className="relative">
            <nav
              aria-label="Principal"
              className="flex gap-1 overflow-x-auto px-1 py-1.5 md:mt-4 md:flex-col md:overflow-x-visible md:px-3"
            >
              {navItems.map((item) => {
                const current = isCurrentSection(pathname, item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    testId={item.testId}
                    variant="rail"
                    ref={current ? currentLinkRef : undefined}
                    aria-current={current ? "page" : undefined}
                    className={[
                      "shrink-0 whitespace-nowrap",
                      current
                        ? "bg-rail-active font-semibold text-rail-active-ink"
                        : "text-rail-muted",
                    ].join(" ")}
                  >
                    {item.icon}
                    {item.label}
                  </Link>
                );
              })}
            </nav>
            <div
              aria-hidden="true"
              className="pointer-events-none absolute inset-y-0 right-0 w-6 bg-linear-to-r from-transparent to-rail md:hidden"
            />
          </div>

          {/*
           * The user block on the phone (task 038): one row that only
           * wraps when the name is long — the name and the role stacked
           * in a small block on the left, the theme select sized to its
           * content with its label hidden (`sr-only`, the accessible name
           * stays "Tema") and "Salir" at the right. The wrapper of the
           * name and the role reads as its `md:contents` children again
           * in the rail column, so the desktop keeps its layout. From md
           * up the visible label comes back.
           */}
          <div className="flex flex-wrap items-center gap-3 px-4 pb-2 md:mt-auto md:flex-col md:items-stretch md:border-t md:border-rail-muted/40 md:px-3 md:py-3">
            <div className="flex flex-col leading-tight md:contents">
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
            </div>
            {/*
             * The theme selector lives in the user block: at the bottom of
             * the rail on desktop, in the same block under the links on the
             * phone layout. It shares the row now instead of taking a row
             * of its own, so the label is visually hidden on the phone.
             */}
            <div className="md:w-auto md:basis-auto">
              <ThemeSelect
                testId="app-theme-select"
                id="app-theme"
                labelClassName="text-rail-ink sr-only md:not-sr-only"
                compact
              />
            </div>
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

        <main
          id="main-content"
          tabIndex={-1}
          className="min-w-0 flex-1 px-4 py-6 md:px-6"
        >
          {children}
        </main>
      </div>
    </>
  );
}
