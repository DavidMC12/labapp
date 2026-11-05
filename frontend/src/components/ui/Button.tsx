import type { ButtonHTMLAttributes } from "react";
import type { TestId } from "@/lib/testid";

type ButtonVariant = "primary" | "secondary" | "rail";

/**
 * The variants of the "Libro mayor" theme. `primary` is the default: an
 * `accent` block with `accent-ink` text. `secondary` is a quiet outline
 * that acts like the primary. `rail` is for buttons that sit on the rail
 * (the logout), text-only and light on the dark green. A hovered variant
 * lightens/darkens with an opacity of its own token; no raw color.
 */
const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: "bg-accent text-accent-ink hover:bg-accent-hover",
  secondary: "bg-transparent text-accent border border-accent hover:bg-ok-bg",
  rail: "bg-transparent text-rail-ink border border-transparent hover:bg-rail-hover",
};

const BASE_CLASSES: string = [
  "inline-flex items-center justify-center gap-2",
  "rounded-md px-[14px] py-[9px]",
  "font-semibold",
  // Touch targets are 44px below 768px and never thinner than 38px.
  "min-h-[44px] md:min-h-[38px]",
  // The only allowed transition: 120ms of color (see globals.css for the
  // reduced-motion opt-out).
  "transition-colors duration-120",
  // A disabled or loading button keeps its shape at 55% opacity.
  "disabled:opacity-55 disabled:cursor-not-allowed",
].join(" ");

type ButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "type"> & {
  type?: "button" | "submit" | "reset";
  testId: TestId;
  loading?: boolean;
  variant?: ButtonVariant;
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
  variant = "primary",
  className,
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
      className={[BASE_CLASSES, VARIANT_CLASSES[variant], className]
        .filter(Boolean)
        .join(" ")}
    />
  );
}
