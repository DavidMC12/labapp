import { describe, expect, it } from "vitest";
import type { Role } from "@/features/auth/types";
import { canManageCustomers } from "./permissions";

describe("canManageCustomers", () => {
  it("is true for admin and sales", () => {
    for (const role of ["admin", "sales"] as const) {
      expect(canManageCustomers(role), role).toBe(true);
    }
  });

  it("is false for finance and readonly", () => {
    for (const role of ["finance", "readonly"] as const) {
      expect(canManageCustomers(role), role).toBe(false);
    }
  });

  it("accepts the exact role type only", () => {
    const roles: Role[] = ["admin", "sales", "finance", "readonly"];
    expect(roles.map(canManageCustomers)).toEqual([true, true, false, false]);
  });
});
