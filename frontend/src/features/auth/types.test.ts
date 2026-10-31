import { describe, expect, it } from "vitest";
import { roleLabel, type Role, type User } from "./types";

describe("roles", () => {
  it("contains exactly the API role values", () => {
    const roles: Role[] = ["admin", "sales", "finance", "readonly"];
    expect(roles).toHaveLength(4);
  });

  it("builds a user with an id, name, email and role", () => {
    const user: User = {
      id: 1,
      name: "Admin Demo",
      email: "admin@labapp.test",
      role: "admin",
    };
    expect(user.role).toBe("admin");
  });
});

describe("roleLabel", () => {
  it("returns the Spanish labels of SPEC section 7", () => {
    expect(roleLabel("admin")).toBe("Admin");
    expect(roleLabel("sales")).toBe("Ventas");
    expect(roleLabel("finance")).toBe("Finanzas");
    expect(roleLabel("readonly")).toBe("Solo lectura");
  });
});
