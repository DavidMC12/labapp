import type { InputHTMLAttributes } from "react";
import { errorTestId, type TestId } from "@/lib/testid";

type InputProps = Omit<InputHTMLAttributes<HTMLInputElement>, "id"> & {
  id: string;
  testId: TestId;
  label: string;
  error?: string;
};

/**
 * Real labeled input: the `label` is linked with `htmlFor` -> `id`, so
 * `getByRole("textbox", { name })` works. When `error` is set, the message
 * is announced with `role="alert"`, carries the derived error test id and is
 * referenced by the input through `aria-describedby`.
 */
export function Input({ id, testId, label, error, ...rest }: InputProps) {
  const hasError = Boolean(error);
  const errorId = errorTestId(testId);

  return (
    <div>
      <label htmlFor={id}>{label}</label>
      <input
        {...rest}
        id={id}
        data-testid={testId}
        aria-invalid={hasError ? "true" : undefined}
        aria-describedby={hasError ? errorId : undefined}
      />
      {error ? (
        <p role="alert" id={errorId} data-testid={errorId}>
          {error}
        </p>
      ) : null}
    </div>
  );
}
