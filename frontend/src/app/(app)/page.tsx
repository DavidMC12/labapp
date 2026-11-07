"use client";

import { Button, Link } from "@/components/ui";
import { useMe } from "@/features/auth/hooks";
import { roleLabel } from "@/features/auth/types";
import {
  formatSummaryCount,
} from "@/features/summary/format";
import {
  useSummary,
  type SummaryCounter,
  type SummaryGroup,
  type SummaryGroupKey,
} from "@/features/summary/hooks";

/** The heading of each section, in Spanish. */
const GROUP_TITLES: Record<SummaryGroupKey, string> = {
  customers: "Clientes",
  orders: "Pedidos",
  invoices: "Facturas",
};

/**
 * One counter card of the summary: a big number over its status label,
 * both inside the link to the filtered list. While the request loads the
 * number is a busy status; a failed request shows "—" (never a blank
 * card) and the section shows its "Reintentar" button.
 */
function CounterCard({ counter }: { counter: SummaryCounter }) {
  if (counter.list.isPending) {
    return (
      <div
        data-testid={counter.loadingTestId}
        role="status"
        aria-busy="true"
        className="rounded-md border border-line bg-surface p-4 text-[13px] text-muted"
      >
        Cargando…
      </div>
    );
  }

  const total = counter.list.data?.total ?? 0;

  return (
    <Link
      href={counter.href}
      testId={counter.linkTestId}
      variant="text"
      className="flex min-w-0 flex-col gap-1 rounded-md border border-line bg-surface p-4 hover:bg-ok-bg"
    >
      <span
        data-testid={counter.countTestId}
        className="text-[26px] font-semibold leading-none tabular-nums"
      >
        {counter.list.isError ? "—" : formatSummaryCount(total)}
      </span>
      <span className="text-[13px] text-muted no-underline">{counter.label}</span>
    </Link>
  );
}

/**
 * One section of the summary: its heading, the counters of the group in a
 * responsive grid (one column on a phone, up to four on a wide screen)
 * and a "Reintentar" button only while any counter of the section has
 * failed.
 */
function SummarySection({ group }: { group: SummaryGroup }) {
  const failed = group.counters.some((counter) => counter.list.isError);

  return (
    <section className="mt-6 min-w-0">
      <h2 data-testid={group.headingTestId}>{GROUP_TITLES[group.key]}</h2>
      <div className="mt-3 grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-4">
        {group.counters.map((counter) => (
          <CounterCard key={counter.status} counter={counter} />
        ))}
      </div>
      {failed ? (
        <div className="mt-3">
          <Button
            testId={group.retryTestId}
            onClick={() => {
              for (const counter of group.counters) {
                void counter.list.refetch();
              }
            }}
          >
            Reintentar
          </Button>
        </div>
      ) : null}
    </section>
  );
}

/**
 * The home "Resumen": a welcome line with the user's role and, for every
 * group, the counters of its statuses as links to the filtered lists.
 * The data comes from `useSummary()` (live totals, shared cache with the
 * lists); the page keeps no count of its own.
 */
export default function HomePage() {
  const me = useMe();
  const summary = useSummary();
  const user = me.data;

  return (
    <div className="min-w-0">
      <h1 data-testid="app-home-heading">Resumen</h1>

      {user ? (
        <p
          data-testid="app-home-greeting-text"
          className="mt-1 text-[15px] text-muted"
        >
          {`Hola, ${user.name} · ${roleLabel(user.role)}`}
        </p>
      ) : null}

      {summary.groups.map((group) => (
        <SummarySection key={group.key} group={group} />
      ))}
    </div>
  );
}
