import { canChangeTaxRate } from "./permissions";
import { describe, expect, it } from "vitest";
import type { Role } from "@/features/auth/types";

describe("canChangeTaxRate", () => {
  const cases: [Role, boolean][] = [
    ["admin", true],
    ["sales", false],
    ["finance", false],
    ["readonly", false],
  ];

  for (const [role, expected] of cases) {
    it(`is ${expected} for ${role}`, () => {
      expect(canChangeTaxRate(role)).toBe(expected);
    });
  }
});
