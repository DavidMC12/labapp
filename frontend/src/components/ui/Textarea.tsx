import type { TextareaHTMLAttributes } from "react";
import { errorTestId, type TestId } from "@/lib/testid";
import { Field, fieldControlProps } from "./Field";

type TextareaProps = Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "id"> & {
  id: string;
  testId: TestId;
  label: string;
  error?: string;
};

/**
 * Real labeled `<textarea>`. Like `Input`, the `label` is linked with
 * `htmlFor` -> `id` and, when `error` is set, the message is announced with
 * `role="alert"`, carries the derived error test id and is referenced by
 * the textarea through `aria-describedby`.
 */
export function Textarea({
  id,
  testId,
  label,
  error,
  ...rest
}: TextareaProps) {
  const errorId = errorTestId(testId);

  return (
    <Field id={id} label={label} errorId={errorId} error={error}>
      <textarea
        {...rest}
        {...fieldControlProps(id, error, errorId)}
        data-testid={testId}
      />
    </Field>
  );
}
