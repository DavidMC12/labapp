import { describe, expect, it } from "vitest";
import { formatDate, formatDateTime, formatMoney, formatTime } from "./format";

describe("formatMoney", () => {
  it("formats the 2-decimal string of the API as USD", () => {
    expect(formatMoney("19.90")).toBe("$19.90");
    expect(formatMoney("1234.50")).toBe("$1,234.50");
    expect(formatMoney("0.00")).toBe("$0.00");
  });

  it("keeps the cents and the grouping of a large total", () => {
    expect(formatMoney("1234567.89")).toBe("$1,234,567.89");
  });
});

describe("formatDate", () => {
  it("formats a timestamp as dd/mm/yyyy in UTC", () => {
    expect(formatDate("2026-10-31T02:30:00Z")).toBe("31/10/2026");
    expect(formatDate("2026-01-01T10:00:00Z")).toBe("01/01/2026");
  });

  it("zero-pads a one-digit day and month", () => {
    // Without the 2-digit options, es-US prints 5/3/2026.
    expect(formatDate("2026-03-05T05:09:00Z")).toBe("05/03/2026");
  });

  it("keeps the UTC calendar day, not the viewer's", () => {
    // 2026-02-27T23:05Z is already the 28th at UTC+1; the UTC date is shown.
    expect(formatDate("2026-02-27T23:05:00Z")).toBe("27/02/2026");
    expect(formatDate("2026-02-28T00:05:00Z")).toBe("28/02/2026");
  });

  it("returns an invalid timestamp unchanged", () => {
    expect(formatDate("not-a-date")).toBe("not-a-date");
  });
});

describe("formatTime", () => {
  it("formats the 23-hour UTC time as hh:mm", () => {
    expect(formatTime("2026-10-31T02:30:00Z")).toBe("02:30");
    expect(formatTime("2026-01-04T15:00:00Z")).toBe("15:00");
  });

  it("zero-pads a one-digit hour and keeps midnight as 00:00", () => {
    expect(formatTime("2026-03-05T05:09:00Z")).toBe("05:09");
    expect(formatTime("2026-01-01T00:00:00Z")).toBe("00:00");
  });

  it("never crosses the next UTC day at midnight", () => {
    expect(formatTime("2026-02-28T23:05:00Z")).toBe("23:05");
    expect(formatTime("2026-02-28T23:59:00Z")).toBe("23:59");
  });

  it("returns an invalid timestamp unchanged, like a date", () => {
    expect(formatTime("not-a-date")).toBe("not-a-date");
  });

  it("shows the UTC suffix instead of the viewer's date on an invalid timestamp", () => {
    expect(formatDateTime("nope")).toBe("nope nope UTC");
  });
});

describe("formatDateTime", () => {
  it("joins the date and time with the UTC suffix", () => {
    expect(formatDateTime("2026-10-31T02:30:00Z")).toBe(
      "31/10/2026 02:30 UTC",
    );
  });

  it("keeps a time close to midnight UTC inside the same day", () => {
    expect(formatDateTime("2026-02-28T23:05:00Z")).toBe(
      "28/02/2026 23:05 UTC",
    );
  });
});
