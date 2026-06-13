import { eq } from "drizzle-orm";
import { getDb } from "../../db";
import {
  discrepancies as discrepanciesTable,
  reconciliationRuns,
  statementTransactions,
} from "../../db/schema";
import { reconcile } from "../engine/reconcile";
import { SEED_FEE_SCHEDULE } from "../engine/fee-schedule";
import type {
  ReconciliationInput,
  ReconciliationResult,
  SettlementTransaction,
} from "../engine/types";

/**
 * Run the engine over a shop's stored transactions and persist a run +
 * its discrepancies. Used by the sync worker after pulling new statements.
 */
export async function runAndStoreForShop(args: {
  shopId: string;
  region: "US" | "GB";
  category?: string;
  uploadId?: string;
}): Promise<ReconciliationResult> {
  const db = getDb();
  const rows = await db
    .select()
    .from(statementTransactions)
    .where(eq(statementTransactions.shopId, args.shopId));

  const transactions = rows.map(rowToTransaction);
  const result = reconcile({
    region: args.region,
    shopCategory: args.category,
    transactions,
  });

  await persistRun({ ...args, result });
  return result;
}

/** Persist an already-computed result (e.g. from the free-tool upload path). */
export async function persistRun(args: {
  shopId?: string;
  uploadId?: string;
  result: ReconciliationResult;
}): Promise<string> {
  const db = getDb();
  const [run] = await db
    .insert(reconciliationRuns)
    .values({
      shopId: args.shopId,
      uploadId: args.uploadId,
      engineVersion: args.result.engineVersion,
      feeScheduleSnapshot: SEED_FEE_SCHEDULE,
      totalOwed: (args.result.totalOwedCents / 100).toFixed(4),
      totals: args.result.summary,
    })
    .returning({ id: reconciliationRuns.id });

  const runId = run!.id;
  if (args.result.discrepancies.length > 0) {
    await db.insert(discrepanciesTable).values(
      args.result.discrepancies.map((d) => ({
        runId,
        shopId: args.shopId,
        checkId: d.checkId,
        ttsOrderId: d.orderId,
        skuId: d.skuId,
        feeType: d.feeType,
        expectedAmount: (d.expected / 100).toFixed(4),
        actualAmount: (d.actual / 100).toFixed(4),
        delta: (d.delta / 100).toFixed(4),
        severity: d.severity,
        context: d.context,
      })),
    );
  }
  return runId;
}

function rowToTransaction(
  row: typeof statementTransactions.$inferSelect,
): SettlementTransaction {
  const n = (v: string | null) => (v ? Math.round(Number(v) * 100) : 0);
  return {
    orderId: row.ttsOrderId,
    skuId: row.skuId ?? undefined,
    type: (row.type as SettlementTransaction["type"]) ?? "order",
    currency: row.currency,
    orderCreatedDate: row.orderCreatedDate ?? undefined,
    grossSales: n(row.grossSales),
    netSales: n(row.netSales),
    customerPayment: n(row.customerPayment),
    platformDiscount: 0,
    sellerDiscount: 0,
    salesTax: n(row.salesTax),
    referralFee: n(row.referralFee),
    transactionFee: n(row.transactionFee),
    refundAdminFee: n(row.refundAdminFee),
    affiliateCommission: n(row.affiliateCommission),
    affiliatePartnerCommission: 0,
    affiliateAdsCommission: 0,
    otherFees: 0,
    shippingActual: n(row.shippingActual),
    shippingCustomerPaid: 0,
    shippingSubsidy: 0,
    fbtFees: n(row.fbtFees),
    adjustmentAmount: n(row.adjustmentAmount),
    adjustmentId: row.adjustmentId ?? undefined,
    grossSalesRefund: 0,
    customerRefund: 0,
    settlementAmount: n(row.settlementAmount),
  };
}

export type { ReconciliationInput };
