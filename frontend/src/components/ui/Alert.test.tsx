import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Alert, ALERT_CLASSES } from "./Alert";

describe("Alert", () => {
  it("keeps the role and the test id", () => {
    render(<Alert testId="auth-login-form-alert">Ingresar falló.</Alert>);

    const alert = screen.getByRole("alert");
    expect(alert).toHaveAttribute("data-testid", "auth-login-form-alert");
    expect(alert).toHaveTextContent("Ingresar falló.");
  });

  it("renders the danger styling of the theme", () => {
    render(<Alert testId="customers-detail-alert">Error.</Alert>);

    for (const className of ["bg-danger-bg", "text-danger", "rounded-md"]) {
      expect(
        (screen.getByTestId("customers-detail-alert").getAttribute("class") ?? "").split(" "),
      ).toContain(className);
    }
  });

  it("carries the focus tabIndex when the alert is focusable", () => {
    render(
      <Alert testId="customers-form-alert" tabIndex={-1}>
        Conflicto de versión.
      </Alert>,
    );

    expect(screen.getByTestId("customers-form-alert")).toHaveAttribute(
      "tabindex",
      "-1",
    );
  });
});
