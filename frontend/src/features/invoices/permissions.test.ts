import { describe, expect, it } from "vitest";
import type { Role } from "@/features/auth/types";
import { canManageInvoices } from "./permissions";

describe("canManageInvoices", () => {
  it("is true for admin and finance", () => {
    for (const role of ["admin", "finance"] as const) {
      expect(canManageInvoices(role), role).toBe(true);
    }
  });

  it("is false for sales and readonly", () => {
    for (const role of ["sales", "readonly"] as const) {
      expect(canManageInvoices(role), role).toBe(false);
    }
  });

  it("accepts the exact role type only", () => {
    const roles: Role[] = ["admin", "sales", "finance", "readonly"];
    expect(roles.map(canManageInvoices)).toEqual([true, false, true, false]);
  });
});
