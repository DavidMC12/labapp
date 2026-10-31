import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Input } from "./Input";

describe("Input", () => {
  it("associates the label with the input by htmlFor and id", () => {
    render(
      <Input
        id="customer-email"
        testId="customers-form-email-input"
        label="Correo electrónico"
      />,
    );

    expect(
      screen.getByLabelText("Correo electrónico"),
    ).toHaveAttribute("id", "customer-email");
  });

  it("renders no alert when there is no error", () => {
    render(
      <Input
        id="customer-email"
        testId="customers-form-email-input"
        label="Correo electrónico"
      />,
    );

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    const input = screen.getByTestId("customers-form-email-input");
    expect(input).not.toHaveAttribute("aria-invalid");
    expect(input).not.toHaveAttribute("aria-describedby");
  });

  it("renders the error alert with the derived error test id", () => {
    render(
      <Input
        id="customer-email"
        testId="customers-form-email-input"
        label="Correo electrónico"
        error="El correo electrónico no es válido."
      />,
    );

    const alert = screen.getByRole("alert");

    expect(alert).toHaveTextContent("El correo electrónico no es válido.");
    expect(alert).toHaveAttribute(
      "data-testid",
      "customers-form-email-error",
    );
    expect(alert.id).toBe("customers-form-email-error");
  });

  it("marks the input invalid and referenced by the error", () => {
    render(
      <Input
        id="customer-email"
        testId="customers-form-email-input"
        label="Correo electrónico"
        error="El correo electrónico no es válido."
      />,
    );

    const input = screen.getByTestId("customers-form-email-input");

    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription(
      "El correo electrónico no es válido.",
    );
  });
});
