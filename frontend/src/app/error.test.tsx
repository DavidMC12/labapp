import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import AppError from "./error";

describe("the error boundary page", () => {
  it("renders the heading, the sentence, the retry button and the home link", () => {
    render(<AppError error={new Error("boom")} reset={() => {}} />);

    expect(screen.getByRole("heading", { name: "Algo salió mal" }))
      .toHaveAttribute("data-testid", "app-error-heading");
    expect(
      screen.getByText(
        "Ocurrió un error inesperado. Puedes intentarlo de nuevo.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reintentar" })).toHaveAttribute(
      "data-testid",
      "app-error-retry-button",
    );
    expect(screen.getByRole("link", { name: "Ir al inicio" })).toHaveAttribute(
      "data-testid",
      "app-error-home-link",
    );
    expect(screen.getByRole("link", { name: "Ir al inicio" })).toHaveAttribute(
      "href",
      "/",
    );
  });

  it("never shows the message or the digest of the crash", () => {
    const error = new Error("detalle secreto de la base de datos");
    Object.assign(error, { digest: "n3v3rdIg3st" });

    render(<AppError error={error} reset={() => {}} />);

    expect(document.body.textContent).not.toContain("detalle secreto");
    expect(document.body.textContent).not.toContain("n3v3rdIg3st");
  });

  it("calls reset when the retry button is clicked", async () => {
    const reset = vi.fn();
    render(<AppError error={new Error("boom")} reset={reset} />);
    const user = userEvent.setup();

    await user.click(screen.getByTestId("app-error-retry-button"));

    expect(reset).toHaveBeenCalledTimes(1);
  });

  it("logs nothing to the console", () => {
    const errorSpy = vi.spyOn(console, "error");
    const inputs = [
      new Error("boom"),
      Object.assign(new Error("boom"), { digest: "d1g3st" }),
      "a string",
      undefined,
    ];

    for (const error of inputs) {
      const { unmount } = render(<AppError error={error} reset={() => {}} />);
      unmount();
    }

    expect(errorSpy).not.toHaveBeenCalled();
  });

  it("sets the document title through the hook", () => {
    render(<AppError error={new Error("boom")} reset={() => {}} />);

    expect(document.title).toBe("Algo salió mal · LabApp");
  });
});
