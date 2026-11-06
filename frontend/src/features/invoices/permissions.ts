/**
 * Permissions of the invoices screens (docs/SPEC.md sections 2 and 6):
 * issuing an invoice and registering a payment are for Admin and Finance
 * only. The server remains the authority.
 */

import type { Role } from "@/features/auth/types";

/** Issue an invoice and register its payments. */
export function canManageInvoices(role: Role): boolean {
  return role === "admin" || role === "finance";
}
