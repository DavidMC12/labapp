/**
 * The counter number of the summary: thousands separators of the es-US
 * locale (docs: `Intl.NumberFormat("es-US")`), so a big list reads as
 * "1,234" and small ones stay plain ("10", "5").
 */

const FORMATTER = new Intl.NumberFormat("es-US");

/** The formatted total of one summary counter. */
export function formatSummaryCount(total: number): string {
  return FORMATTER.format(total);
}
