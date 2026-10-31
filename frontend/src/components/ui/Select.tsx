import type { ReactNode, SelectHTMLAttributes } from "react";
import { errorTestId, type TestId } from "@/lib/testid";
import { Field, fieldControlProps } from "./Field";

type SelectProps = Omit<SelectHTMLAttributes<HTMLSelectElement>, "id"> & {
  id: string;
  testId: TestId;
  label: string;
  error?: string;
  children: ReactNode;
};

/**
 * Real labeled `<select>`; the options are passed as children. Like
 * `Input`, the `label` is linked with `htmlFor` -> `id` and, when `error`
 * is set, the message is announced with `role="alert"`, carries the derived
 * error test id and is referenced by the select through
 * `aria-describedby`.
 */
export function Select({
  id,
  testId,
  label,
  error,
  children,
  ...rest
}: SelectProps) {
  const errorId = errorTestId(testId);

  return (
    <Field id={id} label={label} errorId={errorId} error={error}>
      <select
        {...rest}
        {...fieldControlProps(id, error, errorId)}
        data-testid={testId}
      >
        {children}
      </select>
    </Field>
  );
}
