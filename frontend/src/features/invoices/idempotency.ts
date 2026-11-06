/**
 * Creation of the payment idempotency key (docs/SPEC.md section 6).
 * `crypto.randomUUID` exists only in secure contexts (https, localhost):
 * a developer testing the demo on a phone over a LAN http address would
 * get a thrown error when the form renders. The helper falls back to a
 * version 4 UUID built from `crypto.getRandomValues`, always inside the
 * `^[A-Za-z0-9._-]{1,64}$` shape of the header.
 */
export function newIdempotencyKey(): string {
  const applicationCrypto = globalThis.crypto as
    | { randomUUID?: () => string; getRandomValues?: (bytes: Uint8Array) => Uint8Array }
    | undefined;

  if (typeof applicationCrypto?.randomUUID === "function") {
    return applicationCrypto.randomUUID();
  }

  const bytes = new Uint8Array(16);
  applicationCrypto?.getRandomValues?.(bytes);
  // Version 4 and the RFC variant bits, so the shape is a real UUID.
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;

  const hex = Array.from(bytes, (value) =>
    value.toString(16).padStart(2, "0"),
  );
  return [
    hex.slice(0, 4).join(""),
    hex.slice(4, 6).join(""),
    hex.slice(6, 8).join(""),
    hex.slice(8, 10).join(""),
    hex.slice(10, 16).join(""),
  ].join("-");
}
