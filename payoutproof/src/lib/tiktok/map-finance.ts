import { toCents } from "../money";
import type { SettlementTransaction } from "../engine/types";
import { blankTransaction } from "../ingest/normalize";
import type { RawStatementTransaction } from "./client";

/**
 * Map a Finance API (202501) statement transaction into the same normalized
 * shape the XLSX parser produces. The engine cannot tell the two apart.
 *
 * Sign convention from the API: revenue positive, fee_tax/shipping negative,
 * adjustment signed — matching SettlementTransaction.
 */
export function mapStatementTransaction(
  raw: RawStatementTransaction,
  fallbackCurrency = "USD",
): SettlementTransaction {
  const tx = blankTransaction({
    orderId: String(raw.order_id ?? raw.id ?? "unknown"),
    skuId: raw.sku_id,
    currency: raw.currency ?? fallbackCurrency,
    orderCreatedDate: toIso(raw.order_create_time),
    type: normalizeType(raw.type),
    grossSales: toCents(raw.revenue_amount),
    netSales: toCents(raw.revenue_amount),
    customerPayment: toCents(raw.customer_payment_amount),
    salesTax: toCents(raw.sales_tax_amount),
    referralFee: toCents(raw.referral_fee_amount),
    transactionFee: toCents(raw.transaction_fee_amount),
    refundAdminFee: toCents(raw.refund_administration_fee_amount),
    affiliateCommission: toCents(raw.affiliate_commission_amount),
    shippingActual: toCents(raw.shipping_cost_amount),
    adjustmentAmount: toCents(raw.adjustment_amount),
    adjustmentId: raw.adjustment_id,
    settlementAmount: toCents(raw.settlement_amount),
    raw: raw as unknown as Record<string, unknown>,
  });

  // When the API gives a combined fee_tax bucket but no broken-out referral
  // fee, fold it into otherFees so the consistency check still balances.
  if (tx.referralFee === 0 && raw.fee_tax_amount) {
    tx.otherFees = toCents(raw.fee_tax_amount);
  }

  return tx;
}

function normalizeType(type?: string): SettlementTransaction["type"] {
  if (!type) return "order";
  const t = type.toLowerCase();
  if (t.includes("refund") || t.includes("return")) return "refund";
  if (t.includes("adjust")) return "adjustment";
  if (t.includes("order") || t.includes("settle")) return "order";
  return "other";
}

function toIso(value?: string | number): string | undefined {
  if (value === undefined) return undefined;
  // API timestamps are unix seconds
  if (typeof value === "number") {
    return new Date(value * 1000).toISOString().slice(0, 10);
  }
  const asNum = Number(value);
  if (Number.isFinite(asNum) && asNum > 1_000_000_000) {
    return new Date(asNum * 1000).toISOString().slice(0, 10);
  }
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? undefined : d.toISOString().slice(0, 10);
}
