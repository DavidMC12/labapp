import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Textarea } from "./Textarea";

describe("Textarea", () => {
  it("forwards the ref to the textarea element", () => {
    const controlRef = { current: null as HTMLTextAreaElement | null };

    render(
      <Textarea
        ref={controlRef}
        id="order-notes"
        testId="orders-form-notes-textarea"
        label="Notas"
      />,
    );

    expect(controlRef.current).toBeInstanceOf(HTMLTextAreaElement);
    expect(controlRef.current).toBe(
      screen.getByTestId("orders-form-notes-textarea"),
    );
    controlRef.current?.focus();
    expect(document.activeElement).toBe(
      screen.getByTestId("orders-form-notes-textarea"),
    );
  });

  it("associates the label with the textarea", () => {
    render(
      <Textarea
        id="order-notes"
        testId="orders-form-notes-textarea"
        label="Notas"
      />,
    );

    expect(screen.getByRole("textbox", { name: "Notas" })).toHaveAttribute(
      "id",
      "order-notes",
    );
  });

  it("renders no alert when there is no error", () => {
    render(
      <Textarea
        id="order-notes"
        testId="orders-form-notes-textarea"
        label="Notas"
      />,
    );

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    const textarea = screen.getByTestId("orders-form-notes-textarea");
    expect(textarea).not.toHaveAttribute("aria-invalid");
    expect(textarea).not.toHaveAttribute("aria-describedby");
  });

  it("renders the error alert with the derived error test id", () => {
    render(
      <Textarea
        id="order-notes"
        testId="orders-form-notes-textarea"
        label="Notas"
        error="Las notas no pueden superar los 500 caracteres."
      />,
    );

    const alert = screen.getByRole("alert");

    expect(alert).toHaveTextContent(
      "Las notas no pueden superar los 500 caracteres.",
    );
    expect(alert).toHaveAttribute(
      "data-testid",
      "orders-form-notes-error",
    );
    expect(alert.id).toBe("orders-form-notes-error");
  });

  it("marks the textarea invalid and referenced by the error", () => {
    render(
      <Textarea
        id="order-notes"
        testId="orders-form-notes-textarea"
        label="Notas"
        error="Las notas no pueden superar los 500 caracteres."
      />,
    );

    const textarea = screen.getByTestId("orders-form-notes-textarea");

    expect(textarea).toHaveAttribute("aria-invalid", "true");
    expect(textarea).toHaveAccessibleDescription(
      "Las notas no pueden superar los 500 caracteres.",
    );
  });
});
