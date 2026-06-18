import { describe, it, expect } from "vitest";
import { signRequest } from "../src/lib/tiktok/sign";

describe("signRequest", () => {
  const appSecret = "test_secret";
  const path = "/finance/202501/statements";

  it("is deterministic for the same inputs", () => {
    const args = {
      appSecret,
      path,
      query: { app_key: "key", timestamp: 1700000000, page_size: 50 },
    };
    expect(signRequest(args)).toBe(signRequest(args));
  });

  it("excludes sign and access_token from the signature base", () => {
    const a = signRequest({
      appSecret,
      path,
      query: { app_key: "key", timestamp: 1700000000 },
    });
    const b = signRequest({
      appSecret,
      path,
      query: { app_key: "key", timestamp: 1700000000, sign: "ignored", access_token: "ignored" },
    });
    expect(a).toBe(b);
  });

  it("changes when a real parameter changes", () => {
    const a = signRequest({ appSecret, path, query: { app_key: "key", timestamp: 1 } });
    const b = signRequest({ appSecret, path, query: { app_key: "key", timestamp: 2 } });
    expect(a).not.toBe(b);
  });

  it("incorporates the request body", () => {
    const base = { appSecret, path, query: { app_key: "key", timestamp: 1 } };
    const withBody = signRequest({ ...base, body: '{"a":1}' });
    const without = signRequest(base);
    expect(withBody).not.toBe(without);
  });

  it("produces a 64-char hex digest", () => {
    const sig = signRequest({ appSecret, path, query: { app_key: "key", timestamp: 1 } });
    expect(sig).toMatch(/^[0-9a-f]{64}$/);
  });
});
