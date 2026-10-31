import type { TestId } from "@/lib/testid";
import type { Role } from "./types";

/**
 * The four demo users of docs/SEED.md, in its order, shown on the login
 * screen. Only email and role label are shown; the box is static.
 */
export const DEMO_USERS: {
  email: string;
  role: Role;
  testId: TestId;
}[] = [
  {
    email: "admin@labapp.test",
    role: "admin",
    testId: "auth-login-demo-item-1",
  },
  {
    email: "sales@labapp.test",
    role: "sales",
    testId: "auth-login-demo-item-2",
  },
  {
    email: "finance@labapp.test",
    role: "finance",
    testId: "auth-login-demo-item-3",
  },
  {
    email: "readonly@labapp.test",
    role: "readonly",
    testId: "auth-login-demo-item-4",
  },
];

/** The shared demo password sentence of docs/SEED.md. */
export const DEMO_PASSWORD_TEXT =
  "Contraseña para todos: Demo-LabApp-2026!";
