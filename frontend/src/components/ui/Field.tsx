import type { ReactNode } from "react";

type FieldProps = {
  id: string;
  label: string;
  errorId: string;
  error?: string;
  /** Extra classes for the wrapper, for example a grid column width. */
  className?: string;
  /**
   * Extra classes for the label, for example a rail color. When set, the
   * label color is not the default `text-ink`: the caller owns the color.
   */
  labelClassName?: string;
  /**
   * Keeps the `<label>` linked to the control but visually hidden
   * (`sr-only`): for repeated controls whose column is already labeled,
   * like the quantity inputs of the order lines.
   */
  hideLabel?: boolean;
  children: ReactNode;
};

/**
 * Shared structure of the field components: a label linked with `htmlFor`
 * -> `id` and, when `error` is set, a `role="alert"` paragraph carrying the
 * derived error test id. The control itself is passed as a child; it must
 * set `aria-invalid="true"` and `aria-describedby={errorId}` when there is
 * an error.
 */
export function Field({
  id,
  label,
  errorId,
  error,
  className,
  labelClassName,
  hideLabel = false,
  children,
}: FieldProps) {
  const labelClasses = [
    hideLabel ? "sr-only" : "",
    "text-[13px] font-medium",
    // The caller owns the label color when it passes a custom class; the
    // default is the main text color of the theme.
    labelClassName ?? "text-ink",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      className={["flex flex-col gap-1", className].filter(Boolean).join(" ")}
    >
      <label htmlFor={id} className={labelClasses}>
        {label}
      </label>
      {children}
      {error ? (
        <p
          role="alert"
          id={errorId}
          data-testid={errorId}
          className="text-[13px] font-medium text-danger"
        >
          {error}
        </p>
      ) : null}
    </div>
  );
}

/**
 * Props every field control sets so the label and, when the field has an
 * error, the alert are associated with it.
 */
export function fieldControlProps(controlId: string, error: string | undefined, errorId: string) {
  const hasError = Boolean(error);

  return {
    id: controlId,
    "aria-invalid": hasError ? "true" : undefined,
    "aria-describedby": hasError ? errorId : undefined,
  } as const;
}
