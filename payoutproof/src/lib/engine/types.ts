import type { Cents } from "../money";

export type Region = "US" | "GB";

/**
 * One settlement transaction row, normalized from either the Finance API
 * (202501 statement_transactions) or a Seller Center XLSX export.
 * The engine never knows which source produced it.
 *
 * Sign convention: amounts are stored as TikTok reports them —
 * revenue positive, fees/shipping negative (deductions), adjustments signed.
 */
export interface SettlementTransaction {
  orderId: string;
  skuId?: string;
  statementId?: string;
  statementDate?: string; // ISO date
  orderCreatedDate?: string; // ISO date — drives fee-schedule lookup
  type: "order" | "refund" | "adjustment" | "other";
  currency: string;

  grossSales: Cents;
  netSales: Cents;
  customerPayment: Cents; // what the buyer paid (incl. platform discount, excl. tax) when available
  platformDiscount: Cents;
  sellerDiscount: Cents;
  salesTax: Cents;

  referralFee: Cents; // negative
  transactionFee: Cents; // negative, legacy pre-Apr-2023
  refundAdminFee: Cents; // negative
  affiliateCommission: Cents; // negative
  affiliatePartnerCommission: Cents; // negative
  affiliateAdsCommission: Cents; // negative
  otherFees: Cents; // negative, catch-all

  shippingActual: Cents; // negative
  shippingCustomerPaid: Cents; // positive
  shippingSubsidy: Cents; // positive
  fbtFees: Cents; // negative

  adjustmentAmount: Cents; // signed
  adjustmentId?: string;
  adjustmentReason?: string;

  grossSalesRefund: Cents; // negative on refund rows
  customerRefund: Cents; // negative on refund rows

  settlementAmount: Cents;

  /** Raw source row for audit trail / re-normalization. */
  raw?: Record<string, unknown>;
}

export interface UnsettledOrder {
  orderId: string;
  deliveredDate?: string; // ISO date
  expectedSettlementCents?: Cents;
}

export interface ReconciliationInput {
  region: Region;
  shopCategory?: string; // e.g. "jewelry" — affects referral rate
  transactions: SettlementTransaction[];
  /** Delivered-but-unsettled orders, when order data is available. */
  unsettledOrders?: UnsettledOrder[];
  /** Total reserve/withhold currently held, when known. */
  reserveCents?: Cents;
  reserveOldestDate?: string;
  asOfDate?: string; // defaults to today; injectable for tests
}

export type CheckId =
  | "internal_consistency"
  | "referral_fee"
  | "refund_clawback"
  | "unsettled_aging"
  | "duplicate_adjustment";

export type Severity = "info" | "low" | "medium" | "high";

export interface Discrepancy {
  checkId: CheckId;
  orderId?: string;
  skuId?: string;
  feeType?: string;
  expected: Cents;
  actual: Cents;
  delta: Cents; // positive = seller is owed money
  severity: Severity;
  message: string;
  context?: Record<string, unknown>;
}

export interface Tolerances {
  /** absolute cents below which a delta is ignored (rounding noise) */
  absoluteCents: Cents;
  /** relative fraction of the base below which a delta is ignored */
  relative: number;
  /** days after delivery before an unsettled order is flagged */
  unsettledAgingDays: number;
  /** days a reserve can be held before flagging */
  reserveAgingDays: number;
}

export const DEFAULT_TOLERANCES: Tolerances = {
  absoluteCents: 5, // $0.05 — fee tables round per-SKU; be conservative
  relative: 0.005,
  unsettledAgingDays: 30,
  reserveAgingDays: 45,
};

export interface ReconciliationResult {
  engineVersion: string;
  ranAt: string;
  transactionsChecked: number;
  discrepancies: Discrepancy[];
  /** Sum of positive deltas — the headline "money TikTok may owe you". */
  totalOwedCents: Cents;
  /** Per-check counts for the report summary. */
  summary: Record<CheckId, { count: number; owedCents: Cents }>;
}
