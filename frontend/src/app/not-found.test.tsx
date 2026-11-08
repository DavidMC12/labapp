import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import NotFound from "./not-found";

describe("the not-found page", () => {
  it("renders the heading, the sentence and the home link with their ids", () => {
    render(<NotFound />);

    expect(screen.getByRole("heading", { name: "Página no encontrada" }))
      .toHaveAttribute("data-testid", "app-notfound-heading");
    expect(
      screen.getByText("La dirección que buscas no existe o fue movida."),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ir al inicio" })).toHaveAttribute(
      "data-testid",
      "app-notfound-home-link",
    );
    expect(screen.getByRole("link", { name: "Ir al inicio" })).toHaveAttribute(
      "href",
      "/",
    );
  });
});
