import { and, eq } from "drizzle-orm";
import { getDb } from "../../db";
import { shops, statements, statementTransactions } from "../../db/schema";
import { makeTikTokClient } from "../../lib/tiktok/factory";
import { decryptToken } from "../../lib/crypto";
import { mapStatementTransaction } from "../../lib/tiktok/map-finance";
import { runAndStoreForShop } from "../../lib/services/run-reconciliation";
import type { ShopAuth } from "../../lib/tiktok/client";

export interface SyncShopPayload {
  shopId: string;
}

/**
 * Pull new statements + transactions for one shop since last sync, upsert
 * them, then run reconciliation. Finance data posts ~daily so polling every
 * 6–12h is sufficient; no webhooks required.
 */
export async function syncShop(payload: SyncShopPayload): Promise<void> {
  const db = getDb();
  const [shop] = await db.select().from(shops).where(eq(shops.id, payload.shopId));
  if (!shop || shop.status !== "connected" || !shop.accessTokenEnc || !shop.shopCipher) {
    return;
  }

  const client = makeTikTokClient();
  const auth: ShopAuth = {
    accessToken: decryptToken(shop.accessTokenEnc),
    shopCipher: shop.shopCipher,
  };

  const sinceSeconds = shop.lastSyncedAt
    ? Math.floor(shop.lastSyncedAt.getTime() / 1000)
    : Math.floor(Date.now() / 1000) - 90 * 86_400; // first sync: 90 days back

  let pageToken: string | undefined;
  do {
    const { statements: stmts, nextPageToken } = await client.getStatements(auth, {
      statementTimeGe: sinceSeconds,
      pageToken,
    });

    for (const s of stmts) {
      const [stored] = await db
        .insert(statements)
        .values({
          shopId: shop.id,
          ttsStatementId: s.id,
          statementTime: toDate(s.statement_time),
          currency: s.currency ?? "USD",
          settlementAmount: s.settlement_amount,
          revenueAmount: s.revenue_amount,
          feeAmount: s.fee_amount,
          shippingCostAmount: s.shipping_cost_amount,
          adjustmentAmount: s.adjustment_amount,
          paymentId: s.payment_id,
          source: "api",
          raw: s as unknown as Record<string, unknown>,
        })
        .onConflictDoUpdate({
          target: [statements.shopId, statements.ttsStatementId],
          set: { settlementAmount: s.settlement_amount, raw: s as unknown as Record<string, unknown> },
        })
        .returning({ id: statements.id });

      await syncStatementTransactions(client, auth, shop.id, stored!.id, s.id, s.currency ?? "USD");
    }

    pageToken = nextPageToken;
  } while (pageToken);

  await db.update(shops).set({ lastSyncedAt: new Date() }).where(eq(shops.id, shop.id));

  await runAndStoreForShop({
    shopId: shop.id,
    region: shop.region === "GB" ? "GB" : "US",
    category: shop.category ?? undefined,
  });
}

async function syncStatementTransactions(
  client: ReturnType<typeof makeTikTokClient>,
  auth: ShopAuth,
  shopId: string,
  statementRowId: string,
  ttsStatementId: string,
  currency: string,
): Promise<void> {
  const db = getDb();
  let pageToken: string | undefined;
  do {
    const { transactions, nextPageToken } = await client.getStatementTransactions(
      auth,
      ttsStatementId,
      pageToken,
    );
    for (const raw of transactions) {
      const tx = mapStatementTransaction(raw, currency);
      const major = (cents: number) => (cents / 100).toFixed(4);
      await db
        .insert(statementTransactions)
        .values({
          statementId: statementRowId,
          shopId,
          ttsOrderId: tx.orderId,
          skuId: tx.skuId,
          type: tx.type,
          currency: tx.currency,
          grossSales: major(tx.grossSales),
          netSales: major(tx.netSales),
          customerPayment: major(tx.customerPayment),
          salesTax: major(tx.salesTax),
          referralFee: major(tx.referralFee),
          transactionFee: major(tx.transactionFee),
          refundAdminFee: major(tx.refundAdminFee),
          affiliateCommission: major(tx.affiliateCommission),
          shippingActual: major(tx.shippingActual),
          fbtFees: major(tx.fbtFees),
          adjustmentAmount: major(tx.adjustmentAmount),
          adjustmentId: tx.adjustmentId,
          settlementAmount: major(tx.settlementAmount),
          orderCreatedDate: tx.orderCreatedDate,
          raw: tx.raw,
        })
        .onConflictDoUpdate({
          target: [
            statementTransactions.shopId,
            statementTransactions.ttsOrderId,
            statementTransactions.skuId,
            statementTransactions.type,
          ],
          set: { settlementAmount: major(tx.settlementAmount), raw: tx.raw },
        });
    }
    pageToken = nextPageToken;
  } while (pageToken);
  void and;
  void eq;
}

function toDate(value?: string | number): Date | undefined {
  if (value === undefined) return undefined;
  const n = typeof value === "number" ? value : Number(value);
  if (Number.isFinite(n) && n > 1_000_000_000) return new Date(n * 1000);
  const d = new Date(String(value));
  return Number.isNaN(d.getTime()) ? undefined : d;
}
