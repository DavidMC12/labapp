import type { ReactNode } from "react";
import type { TestId } from "@/lib/testid";

type TableScrollProps = {
  /** The accessible name of the region: what the table lists, for a screen reader. */
  label: string;
  testId: TestId;
  /** Extra classes (the top margin of the table block). */
  className?: string;
  children: ReactNode;
};

/**
 * The scroll container of a table that can be wider than the window. A region that scrolls must be
 * reachable and scrollable from the keyboard (WCAG 2.1.1, the axe rule `scrollable-region-focusable`):
 * it is a focusable `region` with a name, and the global focus style of `globals.css` rings it.
 */
export function TableScroll({ label, testId, className, children }: TableScrollProps) {
  return (
    <div
      role="region"
      aria-label={label}
      tabIndex={0}
      data-testid={testId}
      className={["overflow-x-auto p-1.5", className].filter(Boolean).join(" ")}
    >
      {children}
    </div>
  );
}
