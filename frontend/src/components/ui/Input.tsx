import type { InputHTMLAttributes, Ref } from "react";
import { errorTestId, type TestId } from "@/lib/testid";
import { Field, fieldControlProps } from "./Field";

type InputProps = Omit<InputHTMLAttributes<HTMLInputElement>, "id"> & {
  id: string;
  testId: TestId;
  label: string;
  error?: string;
  /** Visually hides the label; it stays linked for screen readers. */
  hideLabel?: boolean;
  /** React 19 forwards `ref` as a prop. */
  ref?: Ref<HTMLInputElement>;
};

const CONTROL_CLASSES: string = [
  "w-full rounded-md border bg-surface px-[10px]",
  // Touch targets are 44px below 768px; the control is 38px from then up.
  "h-[44px] md:h-[38px]",
  // 16px below 768px: iOS Safari zooms the control on focus at smaller
  // text.
  "text-[16px] md:text-[15px]",
  "text-ink placeholder:text-muted",
  // The only allowed transition: 120ms of color.
  "transition-colors duration-120",
].join(" ");

/**
 * Real labeled input: the `label` is linked with `htmlFor` -> `id`, so
 * `getByRole("textbox", { name })` works. When `error` is set, the message
 * is announced with `role="alert"`, carries the derived error test id and is
 * referenced by the input through `aria-describedby`; the control border
 * becomes `danger`.
 */
export function Input({
  id,
  testId,
  label,
  error,
  hideLabel = false,
  ref: controlRef,
  className,
  ...rest
}: InputProps) {
  const errorId = errorTestId(testId);

  return (
    <Field
      id={id}
      label={label}
      errorId={errorId}
      error={error}
      hideLabel={hideLabel}
    >
      <input
        ref={controlRef}
        {...rest}
        {...fieldControlProps(id, error, errorId)}
        data-testid={testId}
        className={[
          CONTROL_CLASSES,
          error ? "border-danger" : "border-control-border",
          className,
        ]
          .filter(Boolean)
          .join(" ")}
      />
    </Field>
  );
}
