import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Link } from "./Link";

vi.mock("next/link", () => {
  type AnchorProps = {
    href: string;
    children: React.ReactNode;
    "data-testid"?: string;
  };
  function MockedNextLink({
    href,
    children,
    ...rest
  }: AnchorProps) {
    return (
      <a href={href} {...rest}>
        {children}
      </a>
    );
  }
  MockedNextLink.displayName = "Link";
  return { default: MockedNextLink };
});

describe("Link", () => {
  it("renders a real anchor with the test id", () => {
    render(
      <Link href="/customers" testId="customers-new-link">
        Nuevo cliente
      </Link>,
    );

    const link = screen.getByRole("link", { name: "Nuevo cliente" });

    expect(link).toHaveAttribute("href", "/customers");
    expect(link).toHaveAttribute("data-testid", "customers-new-link");
  });
});
