import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Button } from "./Button";

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
