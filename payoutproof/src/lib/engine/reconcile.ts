import {
  buildFeeLookup,
  REFUND_ADMIN_RETENTION,
  type FeeScheduleRow,
  type ShopFeeOverride,
} from "./fee-schedule";
import {
  DEFAULT_TOLERANCES,
  type CheckId,
  type Discrepancy,
  type ReconciliationInput,
  type ReconciliationResult,
  type Severity,
  type SettlementTransaction,
  type Tolerances,
} from "./types";
import { applyRate, type Cents } from "../money";

export const ENGINE_VERSION = "1.0.0";

const CHECK_IDS: CheckId[] = [
  "internal_consistency",
  "referral_fee",
  "refund_clawback",
  "unsettled_aging",
  "duplicate_adjustment",
];

interface EngineOptions {
  tolerances?: Tolerances;
  feeSchedule?: FeeScheduleRow[];
  feeOverrides?: ShopFeeOverride[];
}

/**
 * The reconciliation engine. Pure and deterministic: same input + same
 * fee schedule => same discrepancies. No I/O, no clock reads except the
 * injectable asOfDate. This is what the whole product is built to protect.
 */
export function reconcile(
  input: ReconciliationInput,
  options: EngineOptions = {},
): ReconciliationResult {
  const tol = options.tolerances ?? DEFAULT_TOLERANCES;
  const feeLookup = buildFeeLookup(options.feeSchedule, options.feeOverrides);
  const asOf = input.asOfDate ?? new Date().toISOString().slice(0, 10);

  const discrepancies: Discrepancy[] = [];

  for (const tx of input.transactions) {
    checkInternalConsistency(tx, tol, discrepancies);
    if (tx.type === "order") {
      checkReferralFee(tx, input, feeLookup, tol, discrepancies);
    }
    if (tx.type === "refund") {
      checkRefundClawback(tx, input, feeLookup, tol, discrepancies);
    }
  }

  checkDuplicateAdjustments(input.transactions, discrepancies);
  checkUnsettledAging(input, asOf, tol, discrepancies);

  return summarize(discrepancies, input.transactions.length);
}

/**
 * Check 1 — internal consistency.
 * TikTok's own identity:
 *   revenue + shipping + fees + adjustment = settlement
 * where shipping/fees are already signed (negative for deductions).
 * Catches TikTok's own math/rounding errors and our parse errors.
 */
function checkInternalConsistency(
  tx: SettlementTransaction,
  tol: Tolerances,
  out: Discrepancy[],
): void {
  const revenue = tx.netSales !== 0 ? tx.netSales : tx.grossSales;
  const fees =
    tx.referralFee +
    tx.transactionFee +
    tx.refundAdminFee +
    tx.affiliateCommission +
    tx.affiliatePartnerCommission +
    tx.affiliateAdsCommission +
    tx.otherFees;
  const shipping =
    tx.shippingActual +
    tx.shippingCustomerPaid +
    tx.shippingSubsidy +
    tx.fbtFees;
  const computed = revenue + fees + shipping + tx.adjustmentAmount;
  const delta = tx.settlementAmount - computed;

  if (isWithinTolerance(delta, tx.settlementAmount, tol)) return;

  out.push({
    checkId: "internal_consistency",
    orderId: tx.orderId,
    skuId: tx.skuId,
    expected: computed,
    actual: tx.settlementAmount,
    // If reported settlement is LESS than the components imply, seller is short.
    delta: computed - tx.settlementAmount,
    severity: severityForDelta(computed - tx.settlementAmount),
    message:
      "Statement line does not balance: revenue + shipping + fees + adjustment does not equal the settled amount.",
    context: { revenue, fees, shipping, adjustment: tx.adjustmentAmount },
  });
}

/**
 * Check 2 — expected referral fee.
 * base = customer payment + platform discount − sales tax (US convention).
 * Falls back to gross sales when customerPayment is unavailable (XLSX exports
 * vary). Compares |expected| to |actual referral fee|.
 */
function checkReferralFee(
  tx: SettlementTransaction,
  input: ReconciliationInput,
  feeLookup: ReturnType<typeof buildFeeLookup>,
  tol: Tolerances,
  out: Discrepancy[],
): void {
  const rate = feeLookup.referralRate({
    region: input.region,
    category: input.shopCategory,
    orderDate: tx.orderCreatedDate ?? tx.statementDate,
  });
  if (rate <= 0) return;

  const base =
    tx.customerPayment !== 0
      ? tx.customerPayment + tx.platformDiscount - tx.salesTax
      : tx.grossSales - tx.salesTax;
  if (base <= 0) return;

  const expectedFee = applyRate(base, rate); // positive magnitude
  const actualFee = Math.abs(tx.referralFee);
  // Seller is overcharged when actual fee EXCEEDS expected => owed the excess.
  const delta = actualFee - expectedFee;

  if (isWithinTolerance(delta, expectedFee, tol)) return;

  out.push({
    checkId: "referral_fee",
    orderId: tx.orderId,
    skuId: tx.skuId,
    feeType: "referral",
    expected: expectedFee,
    actual: actualFee,
    delta,
    severity: severityForDelta(delta),
    message:
      delta > 0
        ? `Referral fee charged (${actualFee}) exceeds expected ${(rate * 100).toFixed(1)}% (${expectedFee}).`
        : `Referral fee charged is below expected — verify category/rate.`,
    context: { rate, base },
  });
}

/**
 * Check 3 — refund clawback symmetry.
 * On an eligible refund TikTok returns the referral fee MINUS a 20% admin
 * retention. If the returned referral fee on a refund row is missing or too
 * small, the seller is owed the difference.
 */
function checkRefundClawback(
  tx: SettlementTransaction,
  input: ReconciliationInput,
  feeLookup: ReturnType<typeof buildFeeLookup>,
  tol: Tolerances,
  out: Discrepancy[],
): void {
  const refundedSales = Math.abs(
    tx.grossSalesRefund !== 0 ? tx.grossSalesRefund : tx.customerRefund,
  );
  if (refundedSales <= 0) return;

  const rate = feeLookup.referralRate({
    region: input.region,
    category: input.shopCategory,
    orderDate: tx.orderCreatedDate ?? tx.statementDate,
  });
  const originalFee = applyRate(refundedSales, rate);
  const expectedReturn = applyRate(originalFee, 1 - REFUND_ADMIN_RETENTION);
  // referral fee on a refund row is reported positive (a credit back).
  const actualReturn = tx.referralFee > 0 ? tx.referralFee : Math.abs(tx.referralFee);
  const delta = expectedReturn - actualReturn;

  if (isWithinTolerance(delta, expectedReturn, tol)) return;

  out.push({
    checkId: "refund_clawback",
    orderId: tx.orderId,
    skuId: tx.skuId,
    feeType: "referral_refund",
    expected: expectedReturn,
    actual: actualReturn,
    delta,
    severity: severityForDelta(delta),
    message:
      "Refund did not return the expected referral fee (80% of original after 20% admin retention).",
    context: { refundedSales, rate, originalFee },
  });
}

/**
 * Check 4 — duplicate adjustments.
 * Same adjustmentId appearing on more than one row means the seller was
 * charged (or credited) twice for one event.
 */
function checkDuplicateAdjustments(
  transactions: SettlementTransaction[],
  out: Discrepancy[],
): void {
  const byId = new Map<string, SettlementTransaction[]>();
  for (const tx of transactions) {
    if (!tx.adjustmentId) continue;
    const list = byId.get(tx.adjustmentId) ?? [];
    list.push(tx);
    byId.set(tx.adjustmentId, list);
  }
  for (const [adjustmentId, rows] of byId) {
    if (rows.length < 2) continue;
    // Only a problem when the duplicated adjustment is a debit (negative).
    const duplicatedDebit = rows
      .slice(1)
      .reduce((sum, r) => sum + (r.adjustmentAmount < 0 ? -r.adjustmentAmount : 0), 0);
    if (duplicatedDebit <= 0) continue;
    out.push({
      checkId: "duplicate_adjustment",
      orderId: rows[0]!.orderId,
      feeType: "adjustment",
      expected: Math.abs(rows[0]!.adjustmentAmount),
      actual: rows.reduce((s, r) => s + Math.abs(r.adjustmentAmount), 0),
      delta: duplicatedDebit,
      severity: severityForDelta(duplicatedDebit),
      message: `Adjustment ${adjustmentId} applied ${rows.length} times — possible duplicate charge.`,
      context: { occurrences: rows.length, reason: rows[0]!.adjustmentReason },
    });
  }
}

/**
 * Check 6 — unsettled / withheld money aging.
 * Delivered orders that never settled, and reserves held past the window.
 * Emotionally the strongest finding ("money TikTok is holding").
 */
function checkUnsettledAging(
  input: ReconciliationInput,
  asOf: string,
  tol: Tolerances,
  out: Discrepancy[],
): void {
  const settledOrderIds = new Set(
    input.transactions.filter((t) => t.type === "order").map((t) => t.orderId),
  );

  for (const order of input.unsettledOrders ?? []) {
    if (settledOrderIds.has(order.orderId)) continue;
    if (!order.deliveredDate) continue;
    const ageDays = daysBetween(order.deliveredDate, asOf);
    if (ageDays < tol.unsettledAgingDays) continue;
    const owed = order.expectedSettlementCents ?? 0;
    out.push({
      checkId: "unsettled_aging",
      orderId: order.orderId,
      expected: owed,
      actual: 0,
      delta: owed,
      severity: ageDays > tol.unsettledAgingDays * 2 ? "high" : "medium",
      message: `Order delivered ${ageDays} days ago has no settlement record.`,
      context: { deliveredDate: order.deliveredDate, ageDays },
    });
  }

  if (
    input.reserveCents &&
    input.reserveCents > 0 &&
    input.reserveOldestDate &&
    daysBetween(input.reserveOldestDate, asOf) >= tol.reserveAgingDays
  ) {
    const ageDays = daysBetween(input.reserveOldestDate, asOf);
    out.push({
      checkId: "unsettled_aging",
      expected: input.reserveCents,
      actual: 0,
      delta: input.reserveCents,
      severity: "medium",
      message: `Reserve of held funds is ${ageDays} days old — review release schedule.`,
      context: { reserveOldestDate: input.reserveOldestDate, ageDays },
    });
  }
}

function isWithinTolerance(
  delta: Cents,
  base: Cents,
  tol: Tolerances,
): boolean {
  const abs = Math.abs(delta);
  if (abs <= tol.absoluteCents) return true;
  if (base !== 0 && abs <= Math.abs(base) * tol.relative) return true;
  return false;
}

function severityForDelta(delta: Cents): Severity {
  const abs = Math.abs(delta);
  if (abs >= 5000) return "high"; // >= $50
  if (abs >= 1000) return "medium"; // >= $10
  if (abs >= 100) return "low"; // >= $1
  return "info";
}

function daysBetween(fromIso: string, toIso: string): number {
  const from = new Date(fromIso + "T00:00:00Z").getTime();
  const to = new Date(toIso + "T00:00:00Z").getTime();
  return Math.floor((to - from) / 86_400_000);
}

function summarize(
  discrepancies: Discrepancy[],
  transactionsChecked: number,
): ReconciliationResult {
  const summary = Object.fromEntries(
    CHECK_IDS.map((id) => [id, { count: 0, owedCents: 0 }]),
  ) as ReconciliationResult["summary"];

  let totalOwedCents = 0;
  for (const d of discrepancies) {
    const bucket = summary[d.checkId];
    bucket.count += 1;
    if (d.delta > 0) {
      bucket.owedCents += d.delta;
      totalOwedCents += d.delta;
    }
  }

  return {
    engineVersion: ENGINE_VERSION,
    ranAt: new Date().toISOString(),
    transactionsChecked,
    discrepancies: discrepancies.sort((a, b) => b.delta - a.delta),
    totalOwedCents,
    summary,
  };
}
