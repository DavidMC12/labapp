import type { InputHTMLAttributes } from "react";
import { errorTestId, type TestId } from "@/lib/testid";
import { Field, fieldControlProps } from "./Field";

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
  const errorId = errorTestId(testId);

  return (
    <Field id={id} label={label} errorId={errorId} error={error}>
      <input
        {...rest}
        {...fieldControlProps(id, error, errorId)}
        data-testid={testId}
      />
    </Field>
  );
}
