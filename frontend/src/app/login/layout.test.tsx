import { describe, expect, it } from "vitest";
import LoginLayout, { metadata } from "./layout";

describe("the login layout", () => {
  it("answers the title of the page from the server (the root template adds the suffix)", () => {
    expect(metadata.title).toBe("Iniciar sesión");
  });

  it("renders its children unchanged", () => {
    const child = "the login page";
    expect(LoginLayout({ children: child })).toBe(child);
  });
});
