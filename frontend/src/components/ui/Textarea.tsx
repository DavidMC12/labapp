import { type Ref, type TextareaHTMLAttributes } from "react";
import { errorTestId, type TestId } from "@/lib/testid";
import { Field, fieldControlProps } from "./Field";

type TextareaProps = Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "id"> & {
  id: string;
  testId: TestId;
  label: string;
  error?: string;
  /** React 19 forwards `ref` as a prop. */
  ref?: Ref<HTMLTextAreaElement>;
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
  ref: controlRef,
  ...rest
}: TextareaProps) {
  const errorId = errorTestId(testId);

  return (
    <Field id={id} label={label} errorId={errorId} error={error}>
      <textarea
        ref={controlRef}
        {...rest}
        {...fieldControlProps(id, error, errorId)}
        data-testid={testId}
      />
    </Field>
  );
}
