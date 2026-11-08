import { formatSummaryCount } from "./format";
import { describe, expect, it } from "vitest";

describe("formatSummaryCount", () => {
  it("formats with the thousands separators of es-US", () => {
    // The oracle is Intl itself: both the app and this test read the same
    // ICU data, so the assertion is deterministic.
    expect(formatSummaryCount(1234)).toBe(new Intl.NumberFormat("es-US").format(1234));
    expect(formatSummaryCount(1234567)).toBe(
      new Intl.NumberFormat("es-US").format(1234567),
    );
  });

  it("keeps small numbers plain", () => {
    expect(formatSummaryCount(0)).toBe("0");
    expect(formatSummaryCount(5)).toBe("5");
    expect(formatSummaryCount(10)).toBe("10");
  });
});
