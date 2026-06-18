import { describe, it, expect } from "vitest";
import { toCents, applyRate, formatCents, roundHalfAwayFromZero } from "../src/lib/money";

describe("toCents", () => {
  it("parses plain numbers", () => {
    expect(toCents(12.34)).toBe(1234);
    expect(toCents(0)).toBe(0);
    expect(toCents(-5.5)).toBe(-550);
  });

  it("parses decimal strings with currency symbols and separators", () => {
    expect(toCents("$1,234.56")).toBe(123456);
    expect(toCents("£99.00")).toBe(9900);
    expect(toCents("  12.30  ")).toBe(1230);
  });

  it("treats parentheses as negative (accounting style)", () => {
    expect(toCents("(12.34)")).toBe(-1234);
    expect(toCents("($1,000.00)")).toBe(-100000);
  });

  it("handles empty / null / dash as zero", () => {
    expect(toCents("")).toBe(0);
    expect(toCents(null)).toBe(0);
    expect(toCents(undefined)).toBe(0);
    expect(toCents("-")).toBe(0);
  });

  it("rounds to nearest cent without float drift", () => {
    expect(toCents(0.1 + 0.2)).toBe(30); // 0.30000000000000004 -> 30
    expect(toCents("19.999")).toBe(2000);
  });

  it("throws on garbage", () => {
    expect(() => toCents("not money")).toThrow();
  });
});

describe("applyRate", () => {
  it("computes 6% referral fee on $100", () => {
    expect(applyRate(10000, 0.06)).toBe(600);
  });
  it("rounds half away from zero", () => {
    expect(applyRate(1050, 0.005)).toBe(roundHalfAwayFromZero(5.25)); // 5
    expect(applyRate(1010, 0.05)).toBe(51); // 50.5 -> 51
  });
});

describe("formatCents", () => {
  it("formats USD", () => {
    expect(formatCents(123456)).toBe("$1,234.56");
  });
});
