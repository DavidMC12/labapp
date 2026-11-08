import type { ReactNode, SelectHTMLAttributes } from "react";
import { errorTestId, type TestId } from "@/lib/testid";
import { Field, fieldControlProps } from "./Field";

type SelectProps = Omit<SelectHTMLAttributes<HTMLSelectElement>, "id"> & {
  id: string;
  testId: TestId;
  label: string;
  error?: string;
  /** Extra classes for the label, for example a rail color. */
  labelClassName?: string;
  /** Visually hides the label; it stays linked for screen readers. */
  hideLabel?: boolean;
  /** Sizes to its content on the phone and fills its column from md up. */
  compact?: boolean;
  children: ReactNode;
};

const CONTROL_CLASSES: string = [
  "rounded-md border bg-surface px-[10px]",
  // Touch targets are 44px below 768px; the control is 38px from then up.
  "h-[44px] md:h-[38px]",
  // 16px below 768px: iOS Safari zooms the control on focus at smaller
  // text.
  "text-[16px] md:text-[15px]",
  "text-ink",
  // The only allowed transition: 120ms of color.
  "transition-colors duration-120",
].join(" ");

// The width the control takes. Default: it fills its field. `compact`
// sizes to the content on the phone and fills its column from md up
// (task 038: the theme select shares the user row instead of taking a
// row of its own).
const WIDTH_CLASSES: Record<"full" | "compact", string> = {
  full: "w-full",
  compact: "w-auto md:w-full",
};

/**
 * Real labeled `<select>`; the options are passed as children. Like
 * `Input`, the `label` is linked with `htmlFor` -> `id` and, when `error`
 * is set, the message is announced with `role="alert"`, carries the derived
 * error test id and is referenced by the select through
 * `aria-describedby`; the control border becomes `danger`.
 */
export function Select({
  id,
  testId,
  label,
  error,
  labelClassName,
  hideLabel,
  compact = false,
  children,
  ...rest
}: SelectProps) {
  const errorId = errorTestId(testId);

  return (
    <Field
      id={id}
      label={label}
      errorId={errorId}
      error={error}
      labelClassName={labelClassName}
      hideLabel={hideLabel}
    >
      <select
        {...rest}
        {...fieldControlProps(id, error, errorId)}
        data-testid={testId}
        className={[
          CONTROL_CLASSES,
          compact ? WIDTH_CLASSES.compact : WIDTH_CLASSES.full,
          error ? "border-danger" : "border-control-border",
        ]
          .filter(Boolean)
          .join(" ")}
      >
        {children}
      </select>
    </Field>
  );
}
