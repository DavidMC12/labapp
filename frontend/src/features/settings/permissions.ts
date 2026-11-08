/**
 * Client-side view of the tax-rate permission (docs/SPEC.md section 2:
 * only Admin). The UI hides the form for other roles; the server remains
 * the authority.
 */

import type { Role } from "@/features/auth/types";

/** True only for `admin`. */
export function canChangeTaxRate(role: Role): boolean {
  return role === "admin";
}
