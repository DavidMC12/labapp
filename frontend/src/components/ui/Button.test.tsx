import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Button } from "./Button";

function hasClass(element: HTMLElement, className: string): boolean {
  return element.className.split(" ").includes(className);
}

describe("Button", () => {
  it("renders the test id and keeps the button discoverable", () => {
    render(<Button testId="orders-confirm-button">Confirmar</Button>);

    expect(
      screen.getByRole("button", { name: "Confirmar" }),
    ).not.toBeDisabled();
    expect(screen.getByTestId("orders-confirm-button")).toHaveTextContent(
      "Confirmar",
    );
  });

  it("defaults to idle state and type=button", () => {
    render(<Button testId="app-save-button">Guardar</Button>);

    expect(screen.getByTestId("app-save-button")).toHaveAttribute(
      "data-state",
      "idle",
    );
    expect(screen.getByTestId("app-save-button")).toHaveAttribute(
      "type",
      "button",
    );
    expect(screen.getByTestId("app-save-button")).not.toHaveAttribute(
      "aria-busy",
    );
  });

  it("supports an explicit submit type", () => {
    render(
      <Button type="submit" testId="customers-save-button">
        Guardar
      </Button>,
    );

    expect(screen.getByTestId("customers-save-button")).toHaveAttribute(
      "type",
      "submit",
    );
  });

  it("marks the button busy and disables it while loading", () => {
    render(
      <Button loading testId="orders-confirm-button">
        Confirmar
      </Button>,
    );

    const button = screen.getByTestId("orders-confirm-button");

    expect(button).toHaveAttribute("data-state", "loading");
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(button).toBeDisabled();
  });
});

describe("Button variants", () => {
  it("defaults to the primary variant: accent block with accent-ink text", () => {
    render(<Button testId="app-save-button">Guardar</Button>);

    const button = screen.getByTestId("app-save-button");
    expect(hasClass(button, "bg-accent")).toBe(true);
    expect(hasClass(button, "text-accent-ink")).toBe(true);
  });

  it("styles the secondary variant: transparent with an accent border", () => {
    render(
      <Button variant="secondary" testId="customers-list-prev-button">
        Anterior
      </Button>,
    );

    const button = screen.getByTestId("customers-list-prev-button");
    expect(hasClass(button, "bg-transparent")).toBe(true);
    expect(hasClass(button, "text-accent")).toBe(true);
    expect(hasClass(button, "border-accent")).toBe(true);
    expect(button).not.toBeDisabled();
  });

  it("styles the rail variant light on the dark green rail", () => {
    render(
      <Button variant="rail" testId="app-logout-button">
        Salir
      </Button>,
    );

    const button = screen.getByTestId("app-logout-button");
    expect(hasClass(button, "text-rail-ink")).toBe(true);
    expect(hasClass(button, "border-transparent")).toBe(true);
  });

  it("appends the caller classes after the variant classes", () => {
    render(
      <Button variant="secondary" testId="app-a-button" className="w-full">
        Buscar
      </Button>,
    );

    expect(screen.getByTestId("app-a-button")).toHaveClass("w-full");
  });

  it("keeps the disabled shape at a reduced opacity while loading", () => {
    render(
      <Button loading testId="orders-confirm-button">
        Confirmar
      </Button>,
    );

    const button = screen.getByTestId("orders-confirm-button");
    expect(button).toBeDisabled();
    expect(hasClass(button, "disabled:opacity-55")).toBe(true);
    expect(hasClass(button, "disabled:cursor-not-allowed")).toBe(true);
    // The label survives, so the button keeps an accessible name.
    expect(button).toHaveTextContent("Confirmar");
  });
});
