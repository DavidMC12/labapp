import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Select } from "./Select";

describe("Select", () => {
  it("associates the label with the select and renders its options", () => {
    render(
      <Select
        id="customer-status"
        testId="customers-form-status-select"
        label="Estado"
      >
        <option value="active">Alta</option>
        <option value="archived">Archivado</option>
      </Select>,
    );

    const select = screen.getByRole("combobox", { name: "Estado" });

    expect(select).toHaveAttribute("id", "customer-status");
    expect(
      (screen.getByRole("option", { name: "Alta" }) as HTMLOptionElement)
        .selected,
    ).toBe(true);
    expect(
      screen.getByRole("option", { name: "Alta" }).getAttribute("value"),
    ).toBe("active");
    expect(
      screen.getByRole("option", { name: "Archivado" }).getAttribute("value"),
    ).toBe("archived");
  });

  it("renders no alert when there is no error", () => {
    render(
      <Select
        id="customer-status"
        testId="customers-form-status-select"
        label="Estado"
      >
        <option value="active">Alta</option>
      </Select>,
    );

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    const select = screen.getByTestId("customers-form-status-select");
    expect(select).not.toHaveAttribute("aria-invalid");
    expect(select).not.toHaveAttribute("aria-describedby");
  });

  it("renders the error alert with the derived error test id", () => {
    render(
      <Select
        id="customer-status"
        testId="customers-form-status-select"
        label="Estado"
        error="El estado no es válido."
      >
        <option value="active">Alta</option>
      </Select>,
    );

    const alert = screen.getByRole("alert");

    expect(alert).toHaveTextContent("El estado no es válido.");
    expect(alert).toHaveAttribute("data-testid", "customers-form-status-error");
    expect(alert.id).toBe("customers-form-status-error");
  });

  it("marks the select invalid and referenced by the error", () => {
    render(
      <Select
        id="customer-status"
        testId="customers-form-status-select"
        label="Estado"
        error="El estado no es válido."
      >
        <option value="active">Alta</option>
      </Select>,
    );

    const select = screen.getByTestId("customers-form-status-select");

    expect(select).toHaveAttribute("aria-invalid", "true");
    expect(select).toHaveAccessibleDescription("El estado no es válido.");
  });

  it("derives the error id keeping the numeric suffix", () => {
    render(
      <Select
        id="order-product"
        testId="orders-line-product-select-3"
        label="Producto"
        error="El producto no existe."
      >
        <option value="1">Escuadra</option>
      </Select>,
    );

    expect(screen.getByRole("alert")).toHaveAttribute(
      "data-testid",
      "orders-line-product-error-3",
    );
    expect(screen.getByTestId("orders-line-product-select-3")).toHaveAttribute(
      "aria-describedby",
      "orders-line-product-error-3",
    );
  });

  it("forwards labelClassName to the label instead of the default ink color", () => {
    render(
      <Select
        id="rail-theme"
        testId="app-theme-select"
        label="Tema"
        labelClassName="text-rail-ink"
      >
        <option value="system">Sistema</option>
      </Select>,
    );

    const label = screen.getByText("Tema");

    expect(label).toHaveClass("text-rail-ink");
    expect(label).not.toHaveClass("text-ink");
    expect(label).toHaveClass("text-[13px]", "font-medium");
  });

  it("keeps the default ink label when no labelClassName is given", () => {
    render(
      <Select
        id="list-status"
        testId="customers-list-status-select"
        label="Estado"
      >
        <option value="">Todos</option>
      </Select>,
    );

    expect(screen.getByText("Estado")).toHaveClass("text-ink");
  });

  it("forwards hideLabel to the field so the label stays linked but hidden", () => {
    render(
      <Select
        id="rail-theme"
        testId="app-theme-select"
        label="Tema"
        hideLabel
      >
        <option value="system">Sistema</option>
      </Select>,
    );

    const label = screen.getByText("Tema");

    expect(label).toHaveClass("sr-only");
    expect(screen.getByRole("combobox", { name: "Tema" })).toBeInTheDocument();
  });

  it("sizes to its content on the phone and fills the column from md up when compact", () => {
    render(
      <Select
        id="rail-theme"
        testId="app-theme-select"
        label="Tema"
        compact
      >
        <option value="system">Sistema</option>
      </Select>,
    );

    const select = screen.getByTestId("app-theme-select");

    expect(select).toHaveClass("w-auto", "md:w-full");
    expect(select).not.toHaveClass("w-full");
  });

  it("fills its field when compact is not set", () => {
    render(
      <Select id="list-status" testId="orders-list-status-select" label="Estado">
        <option value="">Todos</option>
      </Select>,
    );

    expect(screen.getByTestId("orders-list-status-select")).toHaveClass(
      "w-full",
    );
  });
});
