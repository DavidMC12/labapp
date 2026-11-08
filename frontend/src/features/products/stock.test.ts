import { describe, expect, it } from "vitest";
import { LOW_STOCK_MAX, OUT_OF_STOCK_MAX, stockState } from "./stock";

describe("stockState", () => {
  it("answers the exact thresholds of the brief", () => {
    const cases: [number, ReturnType<typeof stockState>][] = [
      [0, "agotado"],
      [1, "poco"],
      [5, "poco"],
      [6, null],
    ];
    for (const [stock, expected] of cases) {
      expect(stockState(stock), String(stock)).toBe(expected);
    }
  });

  it("keeps one place for the thresholds", () => {
    expect(OUT_OF_STOCK_MAX).toBe(0);
    expect(LOW_STOCK_MAX).toBe(5);
  });
});
