import { blankTransaction } from "../src/lib/ingest/normalize";
import type { SettlementTransaction } from "../src/lib/engine/types";

/** A clean order: $100 sale, correct 6% referral fee, balances exactly. */
export function cleanOrder(overrides: Partial<SettlementTransaction> = {}): SettlementTransaction {
  return blankTransaction({
    orderId: "ORDER-CLEAN",
    currency: "USD",
    type: "order",
    orderCreatedDate: "2025-09-01",
    grossSales: 10000,
    netSales: 10000,
    customerPayment: 10000,
    salesTax: 0,
    referralFee: -600, // 6% charged correctly
    settlementAmount: 9400, // 10000 - 600
    ...overrides,
  });
}

/** An order where TikTok overcharged the referral fee (9% instead of 6%). */
export function overchargedOrder(): SettlementTransaction {
  return blankTransaction({
    orderId: "ORDER-OVERCHARGE",
    currency: "USD",
    type: "order",
    orderCreatedDate: "2025-09-01",
    grossSales: 10000,
    netSales: 10000,
    customerPayment: 10000,
    referralFee: -900, // should be -600
    settlementAmount: 9100,
  });
}

/** A statement line that does not balance (settlement short by $3.00). */
export function unbalancedOrder(): SettlementTransaction {
  return blankTransaction({
    orderId: "ORDER-UNBALANCED",
    currency: "USD",
    type: "order",
    orderCreatedDate: "2025-09-01",
    grossSales: 10000,
    netSales: 10000,
    customerPayment: 10000,
    referralFee: -600,
    settlementAmount: 9100, // should be 9400 — TikTok kept an extra $3
  });
}

/** A refund that did not return the expected 80% of the referral fee. */
export function shortRefund(): SettlementTransaction {
  return blankTransaction({
    orderId: "ORDER-REFUND",
    currency: "USD",
    type: "refund",
    orderCreatedDate: "2025-09-01",
    grossSalesRefund: -10000,
    customerRefund: -10000,
    referralFee: 0, // should have returned +480 (80% of 600)
    refundAdminFee: 0,
    settlementAmount: -10000,
  });
}
