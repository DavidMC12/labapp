import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SortableHeader } from "./SortableHeader";

describe("SortableHeader", () => {
  it("names the column in a th that carries aria-sort when sorted ascending", () => {
    render(
      <table>
        <thead>
          <tr>
            <SortableHeader
              label="Nombre"
              testId="customers-list-sort-name-button"
              state="ascending"
              onClick={() => {}}
            />
          </tr>
        </thead>
      </table>,
    );

    const cell = screen.getByRole("columnheader", { name: "Nombre" });
    expect(cell).toHaveAttribute("scope", "col");
    expect(cell).toHaveAttribute("aria-sort", "ascending");
  });

  it("carries aria-sort descending when the column sorts descending", () => {
    render(
      <table>
        <thead>
          <tr>
            <SortableHeader
              label="Nombre"
              testId="customers-list-sort-name-button"
              state="descending"
              onClick={() => {}}
            />
          </tr>
        </thead>
      </table>,
    );

    expect(screen.getByRole("columnheader")).toHaveAttribute(
      "aria-sort",
      "descending",
    );
  });

  it("has no aria-sort on an unsorted column", () => {
    render(
      <table>
        <thead>
          <tr>
            <SortableHeader
              label="Nombre"
              testId="customers-list-sort-name-button"
              state="none"
              onClick={() => {}}
            />
          </tr>
        </thead>
      </table>,
    );

    expect(screen.getByRole("columnheader")).not.toHaveAttribute("aria-sort");
  });

  it("is a real button whose accessible name is the label", () => {
    render(
      <table>
        <thead>
          <tr>
            <SortableHeader
              label="Nombre"
              testId="customers-list-sort-name-button"
              state="none"
              onClick={() => {}}
            />
          </tr>
        </thead>
      </table>,
    );

    const button = screen.getByRole("button", { name: "Nombre" });
    expect(button).toHaveAttribute("type", "button");
    expect(button).toHaveAttribute("data-testid", "customers-list-sort-name-button");
    expect(button).toHaveAttribute("data-state", "none");
  });

  it("shows the direction arrow on the sorted column and none on the rest", () => {
    const { rerender } = render(
      <table>
        <thead>
          <tr>
            <SortableHeader
              label="Nombre"
              testId="customers-list-sort-name-button"
              state="descending"
              onClick={() => {}}
            />
          </tr>
        </thead>
      </table>,
    );

    const arrow = screen.getByRole("button", { name: "Nombre" });
    expect(arrow.querySelector("svg")).not.toBeNull();
    expect(arrow.querySelector("svg")).toHaveAttribute("aria-hidden", "true");

    rerender(
      <table>
        <thead>
          <tr>
            <SortableHeader
              label="Nombre"
              testId="customers-list-sort-name-button"
              state="none"
              onClick={() => {}}
            />
          </tr>
        </thead>
      </table>,
    );
    expect(screen.getByRole("button", { name: "Nombre" }).querySelector("svg"))
      .toBeNull();
  });

  it("writes the data-state of the contract on the button", () => {
    const { rerender } = render(
      <table>
        <thead>
          <tr>
            <SortableHeader
              label="Email"
              testId="customers-list-sort-email-button"
              state="ascending"
              onClick={() => {}}
            />
          </tr>
        </thead>
      </table>,
    );

    expect(screen.getByRole("button")).toHaveAttribute("data-state", "ascending");

    rerender(
      <table>
        <thead>
          <tr>
            <SortableHeader
              label="Email"
              testId="customers-list-sort-email-button"
              state="descending"
              onClick={() => {}}
            />
          </tr>
        </thead>
      </table>,
    );
    expect(screen.getByRole("button")).toHaveAttribute("data-state", "descending");
  });

  it("sorts on a click and on the keyboard activation of Enter and Space", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(
      <table>
        <thead>
          <tr>
            <SortableHeader
              label="Nombre"
              testId="customers-list-sort-name-button"
              state="none"
              onClick={onClick}
            />
          </tr>
        </thead>
      </table>,
    );

    await user.tab();
    expect(screen.getByRole("button", { name: "Nombre" })).toHaveFocus();
    await user.keyboard("{Enter}");
    await user.keyboard("{ }");
    // Plus the pointer activation above: three runs of the same handler.
    await user.click(screen.getByRole("button", { name: "Nombre" }));

    expect(onClick).toHaveBeenCalledTimes(3);
  });

  it("keeps the header classes of the page on the cell", () => {
    render(
      <table>
        <thead>
          <tr>
            <SortableHeader
              label="Precio"
              testId="products-list-sort-price-button"
              state="none"
              className="text-right"
              onClick={() => {}}
            />
          </tr>
        </thead>
      </table>,
    );

    expect(screen.getByRole("columnheader")).toHaveClass("text-right");
  });
});
