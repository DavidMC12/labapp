import NextLink from "next/link";
import type { ComponentProps } from "react";
import type { TestId } from "@/lib/testid";

export type LinkVariant = "text" | "primary" | "secondary" | "rail";

/**
 * The variants of the "Libro mayor" theme, matching the Button look where
 * the link acts as a button ("Nuevo cliente"). `text` is the default: an
 * in-line underlined link, with no minimum height (inline text links and
 * table cell links are not touch targets on their own). `rail` is for the
 * navigation rail: it carries no text color of its own, so the brand and
 * the nav links set their token class (`text-rail-ink`, `text-rail-muted`)
 * without a class conflict.
 */
const VARIANT_CLASSES: Record<LinkVariant, string> = {
  text: [
    "text-accent underline underline-offset-2 hover:decoration-2",
    // The only allowed transition: 120ms of color.
    "transition-colors duration-120",
  ].join(" "),
  primary: [
    "no-underline",
    "inline-flex items-center justify-center gap-2 rounded-md px-[14px] py-[9px] font-semibold",
    "min-h-[44px] md:min-h-[38px]",
    "bg-accent text-accent-ink hover:bg-accent-hover",
    "transition-colors duration-120",
  ].join(" "),
  secondary: [
    "no-underline",
    "inline-flex items-center justify-center gap-2 rounded-md px-[14px] py-[9px] font-semibold",
    "min-h-[44px] md:min-h-[38px]",
    "border border-accent bg-transparent text-accent hover:bg-ok-bg",
    "transition-colors duration-120",
  ].join(" "),
  rail: [
    "no-underline",
    "inline-flex items-center gap-2 whitespace-nowrap rounded-md px-3",
    // Rail links are navigation: touch targets, 44px below 768px.
    "min-h-[44px] md:min-h-[38px]",
    "hover:bg-rail-hover",
    "transition-colors duration-120",
  ].join(" "),
};

type LinkProps = ComponentProps<typeof NextLink> & {
  testId: TestId;
  variant?: LinkVariant;
};

/** Wrapper around `next/link` that always renders a `data-testid`. */
export function Link({ testId, variant = "text", className, ...rest }: LinkProps) {
  return (
    <NextLink
      {...rest}
      data-testid={testId}
      className={[VARIANT_CLASSES[variant], className].filter(Boolean).join(" ")}
    />
  );
}
