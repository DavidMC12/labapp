/**
 * Types of the authentication module. The role values and the labels come
 * from docs/SPEC.md sections 2 and 7.
 */

export type Role = "admin" | "sales" | "finance" | "readonly";

export type User = {
  id: number;
  name: string;
  email: string;
  role: Role;
};

export type LoginInput = {
  email: string;
  password: string;
};

const ROLE_LABELS: Record<Role, string> = {
  admin: "Admin",
  sales: "Ventas",
  finance: "Finanzas",
  readonly: "Solo lectura",
};

/** Spanish label of a role, as defined in docs/SPEC.md section 7. */
export function roleLabel(role: Role): string {
  return ROLE_LABELS[role];
}
