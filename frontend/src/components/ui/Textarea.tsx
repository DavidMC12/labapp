import type { Ref, TextareaHTMLAttributes } from "react";
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

const CONTROL_CLASSES: string = [
  "w-full rounded-md border bg-surface px-[10px] py-1.5",
  // The textarea is at least 96px high; same touch target as the other
  // controls below 768px.
  "min-h-[96px]",
  "text-[15px] text-ink placeholder:text-muted",
  // The only allowed transition: 120ms of color.
  "transition-colors duration-120",
].join(" ");

/**
 * Real labeled `<textarea>`. Like `Input`, the `label` is linked with
 * `htmlFor` -> `id` and, when `error` is set, the message is announced with
 * `role="alert"`, carries the derived error test id and is referenced by
 * the textarea through `aria-describedby`; the control border becomes
 * `danger`.
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
        className={[
          CONTROL_CLASSES,
          error ? "border-danger" : "border-control-border",
        ]
          .filter(Boolean)
          .join(" ")}
      />
    </Field>
  );
}
