import type { TestId } from "@/lib/testid";

/**
 * The observable sort state of one column, written as `data-state` on the
 * button and read from it by the tests. It is the direction of the active
 * sort of the column, `none` when the table is not sorted by it.
 */
export type SortableHeaderState = "ascending" | "descending" | "none";

type SortableHeaderProps = {
  /** The column label: the visible text, so the accessible name of the button. */
  label: string;
  testId: TestId;
  /** The direction the column sorts now, or `none` when it is not the sorted one. */
  state: SortableHeaderState;
  /** The header classes of the page (the ledger header cell style). */
  className?: string;
  /** What a click does: the pages run their sort toggle with this. */
  onClick: () => void;
};

/**
 * The arrow of the sorted column (up when ascending, down when
 * descending, the stroke icon style of the app shell). It carries no
 * information for assistive technology — the direction is already in the
 * label position, in `aria-sort` — so it is hidden from it.
 */
function SortArrow({ direction }: { direction: "ascending" | "descending" }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 8 12"
      width="8"
      height="12"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="shrink-0"
    >
      {direction === "ascending"
        ? <path d="M4 10.5V1.5M1 4.5l3-3 3 3" />
        : <path d="M4 1.5v9M1 7.5l3 3 3-3" />}
    </svg>
  );
}

/**
 * The header cell of one sortable column: a `<th scope="col">` with
 * `aria-sort` naming the direction whenever the table is sorted by it,
 * and inside it a real `<button>` the keyboard can use. Clicking the
 * button sorts or flips the sort (the pages own that decision); the
 * rest of the announcement is the `role="status"` element of the page.
 */
export function SortableHeader({
  label,
  testId,
  state,
  className,
  onClick,
}: SortableHeaderProps) {
  return (
    <th scope="col" className={className} aria-sort={state === "none" ? undefined : state}>
      <button
        type="button"
        data-testid={testId}
        data-state={state}
        onClick={onClick}
        className={[
          "inline-flex min-h-[24px] min-w-[24px] items-center gap-1",
          "text-xs font-medium uppercase tracking-[0.07em] text-muted",
          "hover:text-ink",
          "transition-colors duration-120",
          "cursor-pointer",
        ].join(" ")}
      >
        {label}
        {state === "none" ? null : <SortArrow direction={state} />}
      </button>
    </th>
  );
}
