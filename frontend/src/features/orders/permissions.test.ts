import { describe, expect, it } from "vitest";
import type { Role } from "@/features/auth/types";
import { canEditOrders, canTransitionOrders } from "./permissions";

describe("the orders permissions", () => {
  it("allows both to admin and sales", () => {
    for (const role of ["admin", "sales"] as const) {
      expect(canEditOrders(role), `edit: ${role}`).toBe(true);
      expect(canTransitionOrders(role), `transition: ${role}`).toBe(true);
    }
  });

  it("denies both to finance and readonly", () => {
    for (const role of ["finance", "readonly"] as const) {
      expect(canEditOrders(role), `edit: ${role}`).toBe(false);
      expect(canTransitionOrders(role), `transition: ${role}`).toBe(false);
    }
  });

  it("accepts the exact role type only", () => {
    const roles: Role[] = ["admin", "sales", "finance", "readonly"];
    expect(roles.map(canEditOrders)).toEqual([true, true, false, false]);
    expect(roles.map(canTransitionOrders)).toEqual([true, true, false, false]);
  });
});
