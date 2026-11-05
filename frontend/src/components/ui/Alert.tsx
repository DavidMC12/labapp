import type { ReactNode, Ref } from "react";
import type { TestId } from "@/lib/testid";

/**
 * The classes of every error alert, shared with the field-level error
 * paragraphs of `Field`. Kept `danger` text on `danger-bg` per the theme.
 */
export const ALERT_CLASSES =
  "rounded-md bg-danger-bg px-[12px] py-[10px] text-[13px] font-medium text-danger";

type AlertProps = {
  testId: TestId;
  children: ReactNode;
  tabIndex?: number;
  /** React 19 forwards `ref` as a prop. */
  ref?: Ref<HTMLParagraphElement>;
};

/**
 * The page- and form-level error paragraph: stays a `<p role="alert">` with
 * its existing test id, rendered with the danger styling of the theme.
 */
export function Alert({ testId, children, tabIndex, ref }: AlertProps) {
  return (
    <p
      ref={ref}
      role="alert"
      data-testid={testId}
      tabIndex={tabIndex}
      className={ALERT_CLASSES}
    >
      {children}
    </p>
  );
}
