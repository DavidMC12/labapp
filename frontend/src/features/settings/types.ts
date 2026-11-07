/**
 * Types of the Settings API (docs/SPEC.md section 5, "Orders API",
 * "Settings" rule).
 */

/** The current settings: only the tax rate today, as a string with 2 decimals. */
export type Settings = {
  tax_rate: string;
};
