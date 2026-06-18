import { describe, it, expect, beforeAll } from "vitest";

describe("session signing", () => {
  beforeAll(() => {
    process.env.SESSION_SECRET = "test-session-secret-please-change";
  });

  it("round-trips an account session", async () => {
    const { encodeSession, decodeSession } = await import("../src/lib/auth/session");
    const token = encodeSession({ accountId: "acc-1", email: "a@b.com" });
    const data = decodeSession(token);
    expect(data?.accountId).toBe("acc-1");
    expect(data?.email).toBe("a@b.com");
    expect(typeof data?.iat).toBe("number");
  });

  it("rejects a tampered payload", async () => {
    const { encodeSession, decodeSession } = await import("../src/lib/auth/session");
    const token = encodeSession({ accountId: "acc-1", email: "a@b.com" });
    const [, mac] = token.split(".");
    const forgedPayload = Buffer.from(
      JSON.stringify({ accountId: "attacker", email: "x@y.com", iat: Math.floor(Date.now() / 1000) }),
    ).toString("base64url");
    expect(decodeSession(`${forgedPayload}.${mac}`)).toBeNull();
  });

  it("rejects malformed and empty tokens", async () => {
    const { decodeSession } = await import("../src/lib/auth/session");
    expect(decodeSession(undefined)).toBeNull();
    expect(decodeSession("garbage")).toBeNull();
    expect(decodeSession("a.b.c")).toBeNull();
  });

  it("rejects an expired session", async () => {
    const { decodeSession } = await import("../src/lib/auth/session");
    const { createHmac } = await import("node:crypto");
    const old = Math.floor(Date.now() / 1000) - 60 * 60 * 24 * 40; // 40 days ago
    const payload = Buffer.from(
      JSON.stringify({ accountId: "acc-1", email: "a@b.com", iat: old }),
    ).toString("base64url");
    const mac = createHmac("sha256", process.env.SESSION_SECRET!).update(payload).digest("base64url");
    expect(decodeSession(`${payload}.${mac}`)).toBeNull();
  });
});
