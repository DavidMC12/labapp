/**
 * Permissions of the orders screens (docs/SPEC.md section 5): creating an
 * order, changing its customer and editing its lines need the permission
 * to edit draft orders; confirming, cancelling and shipping need the
 * permission to transition orders. The server remains the authority.
 */

import type { Role } from "@/features/auth/types";

/** Draft editing: create, change the customer, add/edit/remove lines. */
export function canEditOrders(role: Role): boolean {
  return role === "admin" || role === "sales";
}

/** Transitions: confirm, cancel and ship. */
export function canTransitionOrders(role: Role): boolean {
  return role === "admin" || role === "sales";
}
