/**
 * Client-side view of the customer-management permission (docs/SPEC.md
 * section 2: Admin and Sales). The UI hides the write controls for other
 * roles; the server remains the authority.
 */

import type { Role } from "@/features/auth/types";

/** True only for `admin` and `sales`. */
export function canManageCustomers(role: Role): boolean {
  return role === "admin" || role === "sales";
}
