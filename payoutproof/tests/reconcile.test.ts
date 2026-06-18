import { describe, it, expect } from "vitest";
import { reconcile, ENGINE_VERSION } from "../src/lib/engine/reconcile";
import type { ReconciliationInput } from "../src/lib/engine/types";
import {
  cleanOrder,
  overchargedOrder,
  unbalancedOrder,
  shortRefund,
} from "./fixtures";

function input(partial: Partial<ReconciliationInput>): ReconciliationInput {
  return {
    region: "US",
    transactions: [],
    asOfDate: "2026-06-13",
    ...partial,
  };
}

describe("reconcile — clean data", () => {
  it("finds nothing wrong with a correct order", () => {
    const result = reconcile(input({ transactions: [cleanOrder()] }));
    expect(result.discrepancies).toHaveLength(0);
    expect(result.totalOwedCents).toBe(0);
    expect(result.engineVersion).toBe(ENGINE_VERSION);
  });

  it("ignores sub-cent rounding noise within tolerance", () => {
    const tx = cleanOrder({ settlementAmount: 9397 }); // $0.03 off, within $0.05
    const result = reconcile(input({ transactions: [tx] }));
    expect(result.discrepancies).toHaveLength(0);
  });
});

describe("check: referral fee overcharge", () => {
  it("flags a 9% fee where 6% was expected and computes the owed delta", () => {
    const result = reconcile(input({ transactions: [overchargedOrder()] }));
    const ref = result.discrepancies.find((d) => d.checkId === "referral_fee");
    expect(ref).toBeDefined();
    expect(ref!.delta).toBe(300); // 900 charged - 600 expected
    expect(result.totalOwedCents).toBeGreaterThanOrEqual(300);
  });

  it("uses the jewelry 5% rate when category is jewelry", () => {
    const tx = cleanOrder({ referralFee: -600 }); // 6% charged
    const result = reconcile(
      input({ shopCategory: "jewelry", transactions: [tx] }),
    );
    // expected 5% = 500, charged 600 => owed 100
    const ref = result.discrepancies.find((d) => d.checkId === "referral_fee");
    expect(ref?.delta).toBe(100);
  });

  it("respects a new-seller 3% promo override", () => {
    const tx = cleanOrder({ referralFee: -600 });
    const result = reconcile(
      input({ transactions: [tx] }),
      {
        feeOverrides: [
          { feeType: "referral", rate: 0.03, effectiveFrom: "2025-08-01", effectiveTo: "2025-09-30" },
        ],
      },
    );
    // expected 3% = 300, charged 600 => owed 300
    const ref = result.discrepancies.find((d) => d.checkId === "referral_fee");
    expect(ref?.delta).toBe(300);
  });
});

describe("check: internal consistency", () => {
  it("flags a statement line that does not balance", () => {
    const result = reconcile(input({ transactions: [unbalancedOrder()] }));
    const c = result.discrepancies.find((d) => d.checkId === "internal_consistency");
    expect(c).toBeDefined();
    expect(c!.delta).toBe(300); // shorted $3.00
  });
});

describe("check: refund clawback", () => {
  it("flags a refund that did not return 80% of the referral fee", () => {
    const result = reconcile(input({ transactions: [shortRefund()] }));
    const c = result.discrepancies.find((d) => d.checkId === "refund_clawback");
    expect(c).toBeDefined();
    // original fee 6% of 10000 = 600; expected return 80% = 480; actual 0
    expect(c!.delta).toBe(480);
  });
});

describe("check: unsettled aging", () => {
  it("flags a delivered order with no settlement record older than 30 days", () => {
    const result = reconcile(
      input({
        transactions: [cleanOrder()],
        unsettledOrders: [
          { orderId: "ORDER-LOST", deliveredDate: "2026-04-01", expectedSettlementCents: 5000 },
        ],
      }),
    );
    const c = result.discrepancies.find((d) => d.checkId === "unsettled_aging");
    expect(c).toBeDefined();
    expect(c!.delta).toBe(5000);
    expect(c!.severity).toBe("high"); // > 60 days old
  });

  it("does not flag an unsettled order that already has a settlement row", () => {
    const result = reconcile(
      input({
        transactions: [cleanOrder({ orderId: "ORDER-X" })],
        unsettledOrders: [
          { orderId: "ORDER-X", deliveredDate: "2026-04-01", expectedSettlementCents: 5000 },
        ],
      }),
    );
    expect(result.discrepancies.find((d) => d.checkId === "unsettled_aging")).toBeUndefined();
  });

  it("flags an aged reserve", () => {
    const result = reconcile(
      input({
        transactions: [cleanOrder()],
        reserveCents: 12000,
        reserveOldestDate: "2026-01-01",
      }),
    );
    expect(result.discrepancies.some((d) => d.checkId === "unsettled_aging")).toBe(true);
  });
});

describe("check: duplicate adjustments", () => {
  it("flags the same adjustment id charged twice", () => {
    const a = cleanOrder({ orderId: "O1", adjustmentId: "ADJ-1", adjustmentAmount: -500, type: "adjustment", grossSales: 0, netSales: 0, customerPayment: 0, referralFee: 0, settlementAmount: -500 });
    const b = cleanOrder({ orderId: "O2", adjustmentId: "ADJ-1", adjustmentAmount: -500, type: "adjustment", grossSales: 0, netSales: 0, customerPayment: 0, referralFee: 0, settlementAmount: -500 });
    const result = reconcile(input({ transactions: [a, b] }));
    const c = result.discrepancies.find((d) => d.checkId === "duplicate_adjustment");
    expect(c).toBeDefined();
    expect(c!.delta).toBe(500); // one duplicated $5 debit
  });
});

describe("summary + sorting", () => {
  it("aggregates owed totals per check and sorts findings by delta desc", () => {
    const result = reconcile(
      input({ transactions: [overchargedOrder(), unbalancedOrder(), cleanOrder()] }),
    );
    expect(result.transactionsChecked).toBe(3);
    expect(result.totalOwedCents).toBeGreaterThan(0);
    const deltas = result.discrepancies.map((d) => d.delta);
    expect([...deltas].sort((a, b) => b - a)).toEqual(deltas);
  });
});
