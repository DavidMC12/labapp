import type { ReactNode } from "react";

type FieldProps = {
  id: string;
  label: string;
  errorId: string;
  error?: string;
  /** Extra classes for the wrapper, for example a grid column width. */
  className?: string;
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
  children,
}: FieldProps) {
  return (
    <div
      className={["flex flex-col gap-1", className].filter(Boolean).join(" ")}
    >
      <label htmlFor={id} className="text-[13px] font-medium text-ink">
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
