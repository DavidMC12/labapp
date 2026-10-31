import type { ReactNode } from "react";

type FieldProps = {
  id: string;
  label: string;
  errorId: string;
  error?: string;
  children: ReactNode;
};

/**
 * Shared structure of the field components: a label linked with `htmlFor`
 * -> `id` and, when `error` is set, a `role="alert"` paragraph carrying the
 * derived error test id. The control itself is passed as a child; it must
 * set `aria-invalid="true"` and `aria-describedby={errorId}` when there is
 * an error.
 */
export function Field({ id, label, errorId, error, children }: FieldProps) {
  return (
    <div>
      <label htmlFor={id}>{label}</label>
      {children}
      {error ? (
        <p role="alert" id={errorId} data-testid={errorId}>
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
