import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { newIdempotencyKey } from "./idempotency";

const KEY_SHAPE = /^[A-Za-z0-9._-]{1,64}$/;

beforeEach(() => {
  vi.unstubAllGlobals();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("newIdempotencyKey", () => {
  it("uses crypto.randomUUID when it exists", () => {
    const key = newIdempotencyKey();
    expect(key).toMatch(KEY_SHAPE);
    // A UUID v4: the version nibble of the third group and the variant.
    expect(key.split("-")[2][0]).toBe("4");
    expect(key.split("-")[3][0]).toMatch(/^[89ab]$/);
  });

  it("keeps working when only randomUUID is exposed", () => {
    vi.stubGlobal("crypto", {
      randomUUID: () => "fedcba98-7654-4321-8abc-def012345678",
    });
    expect(newIdempotencyKey()).toBe("fedcba98-7654-4321-8abc-def012345678");
  });

  it("builds a version 4 UUID from getRandomValues without randomUUID", () => {
    // The http LAN context of a developer testing on a phone.
    vi.stubGlobal("crypto", {
      getRandomValues: (bytes: Uint8Array) => {
        for (let index = 0; index < bytes.length; index += 1) {
          bytes[index] = (index * 17 + 3) % 256;
        }
        return bytes;
      },
    });

    const key = newIdempotencyKey();
    expect(key).toMatch(KEY_SHAPE);
    expect(key.length).toBe(36);
    // The fixed version and variant bits of a version 4 UUID.
    expect(key.split("-")[2][0]).toBe("4");
    expect(key.split("-")[3][0]).toMatch(/^[89ab]$/);
  });
});
