import { describe, it, expect, beforeAll } from "vitest";
import { randomBytes } from "node:crypto";

describe("token encryption", () => {
  beforeAll(() => {
    process.env.ENCRYPTION_KEY = randomBytes(32).toString("base64");
  });

  it("round-trips a token through encrypt/decrypt", async () => {
    const { encryptToken, decryptToken } = await import("../src/lib/crypto");
    const secret = "tts-access-token-abc123";
    const enc = encryptToken(secret);
    expect(enc).not.toContain(secret);
    expect(decryptToken(enc)).toBe(secret);
  });

  it("produces different ciphertext each time (random IV)", async () => {
    const { encryptToken } = await import("../src/lib/crypto");
    expect(encryptToken("x")).not.toBe(encryptToken("x"));
  });

  it("fails to decrypt tampered ciphertext", async () => {
    const { encryptToken, decryptToken } = await import("../src/lib/crypto");
    const enc = encryptToken("secret");
    const [iv, tag, ct] = enc.split(".");
    const tampered = [iv, tag, Buffer.from("evil").toString("base64")].join(".");
    void ct;
    expect(() => decryptToken(tampered)).toThrow();
  });
});
