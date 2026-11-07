/**
 * Requests of the Settings API (docs/SPEC.md section 5, "Orders API",
 * "Settings" rule), all through the thin client of `src/lib/api.ts`. The
 * tax rate travels exactly as typed: the field is a string of format
 * `^[0-9]{1,3}(\.[0-9]{1,2})?$` between 0.00 and 100.00, and the server
 * decides what is valid.
 */

import { apiFetch } from "@/lib/api";
import type { Settings } from "./types";

/** GET /api/settings — 200 `Settings` (every role). */
export function fetchSettings(): Promise<Settings> {
  return apiFetch<Settings>("/api/settings");
}

/**
 * PATCH /api/settings — 200 `Settings` (Admin). The body is
 * `{"tax_rate": "<the string exactly as typed>"}`: this client never
 * trims, parses or reformats it, so the server answers like the owner's
 * tests expect (" 7", "1e1" and "10.123" come back as errors).
 */
export function updateTaxRate(taxRate: string): Promise<Settings> {
  return apiFetch<Settings>("/api/settings", {
    method: "PATCH",
    body: { tax_rate: taxRate },
  });
}
