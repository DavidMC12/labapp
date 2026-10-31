import NextLink from "next/link";
import type { ComponentProps } from "react";
import type { TestId } from "@/lib/testid";

type LinkProps = ComponentProps<typeof NextLink> & {
  testId: TestId;
};

/** Wrapper around `next/link` that always renders a `data-testid`. */
export function Link({ testId, ...rest }: LinkProps) {
  return <NextLink {...rest} data-testid={testId} />;
}
