import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Link, type LinkVariant } from "./Link";
import type { TestId } from "@/lib/testid";

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

  describe("variants", () => {
    function renderVariant(variant?: LinkVariant, testId?: TestId) {
      render(
        <Link
          href="/customers/new"
          variant={variant}
          testId={testId ?? "customers-new-link"}
        >
          Nuevo cliente
        </Link>,
      );
    }

    function hasClass(element: Element, className: string): boolean {
      return (element.getAttribute("class") ?? "").split(" ").includes(className);
    }

    it("defaults to the text variant: accent, underlined, thicker on hover", () => {
      renderVariant();
      const link = screen.getByTestId("customers-new-link");

      expect(hasClass(link, "text-accent")).toBe(true);
      expect(hasClass(link, "underline")).toBe(true);
      expect(hasClass(link, "hover:decoration-2")).toBe(true);
      expect(hasClass(link, "no-underline")).toBe(false);
    });

    it("styles the primary variant like the primary button", () => {
      renderVariant("primary", "customers-new-link");
      const link = screen.getByTestId("customers-new-link");

      expect(hasClass(link, "bg-accent")).toBe(true);
      expect(hasClass(link, "text-accent-ink")).toBe(true);
      expect(hasClass(link, "no-underline")).toBe(true);
      expect(hasClass(link, "min-h-[44px]")).toBe(true);
      expect(hasClass(link, "md:min-h-[38px]")).toBe(true);
    });

    it("styles the secondary variant like the secondary button", () => {
      renderVariant("secondary", "customers-detail-edit-link");
      const link = screen.getByTestId("customers-detail-edit-link");

      expect(hasClass(link, "border-accent")).toBe(true);
      expect(hasClass(link, "bg-transparent")).toBe(true);
      expect(hasClass(link, "text-accent")).toBe(true);
      expect(hasClass(link, "no-underline")).toBe(true);
    });

    it("styles the rail variant for the navigation rail", () => {
      renderVariant("rail", "app-nav-customers-link");
      const link = screen.getByTestId("app-nav-customers-link");

      expect(hasClass(link, "hover:bg-rail-hover")).toBe(true);
      expect(hasClass(link, "no-underline")).toBe(true);
    });

    it("keeps href, test id and caller classes in every variant", () => {
      render(
        <Link
          href="/customers"
          variant="primary"
          className="w-full"
          testId="customers-new-link"
        >
          Nuevo cliente
        </Link>,
      );
      const link = screen.getByTestId("customers-new-link");

      expect(link).toHaveAttribute("href", "/customers");
      expect(hasClass(link, "w-full")).toBe(true);
    });
  });
});
