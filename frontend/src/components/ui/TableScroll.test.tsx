import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TableScroll } from "./TableScroll";

describe("TableScroll", () => {
  it("is a named, focusable region around its table so the keyboard can scroll it", () => {
    render(
      <TableScroll testId="orders-list-scroll-region" label="Tabla de pedidos" className="mt-6">
        <table>
          <tbody>
            <tr>
              <td>una celda</td>
            </tr>
          </tbody>
        </table>
      </TableScroll>,
    );

    const region = screen.getByRole("region", { name: "Tabla de pedidos" });
    expect(region).toHaveAttribute("tabindex", "0");
    expect(region).toHaveAttribute("data-testid", "orders-list-scroll-region");
    expect(region).toHaveClass("overflow-x-auto", "mt-6");
    expect(region).toContainElement(screen.getByRole("table"));
  });
});
