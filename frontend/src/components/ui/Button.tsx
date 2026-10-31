import type { ButtonHTMLAttributes } from "react";
import type { TestId } from "@/lib/testid";

type ButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "type"> & {
  type?: "button" | "submit" | "reset";
  testId: TestId;
  loading?: boolean;
};

/**
 * Real native button. `loading` marks the button busy and disables it, so
 * tests can read the state from `data-state` and `aria-busy` instead of
 * clicking through in-flight requests.
 */
export function Button({
  type = "button",
  testId,
  loading = false,
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      type={type}
      data-testid={testId}
      aria-busy={loading ? "true" : undefined}
      data-state={loading ? "loading" : "idle"}
      disabled={disabled || loading}
    />
  );
}
