import { and, desc, eq, inArray, sql } from "drizzle-orm";
import { getDb } from "../../db";
import {
  discrepancies,
  reconciliationRuns,
  sellerAccounts,
  shops,
} from "../../db/schema";

export interface DashboardData {
  email: string;
  plan: string;
  planStatus: string;
  shops: { id: string; name: string | null; region: string; status: string; lastSyncedAt: Date | null }[];
  openCount: number;
  openOwedCents: number;
  recoveredCents: number;
  latestRunAt: Date | null;
  topFindings: FindingRow[];
}

export interface FindingRow {
  id: string;
  checkId: string;
  orderId: string | null;
  feeType: string | null;
  deltaCents: number;
  severity: string;
  status: string;
}

const toCents = (v: string | null) => (v ? Math.round(Number(v) * 100) : 0);

export async function getDashboardData(accountId: string): Promise<DashboardData | null> {
  const db = getDb();
  const [account] = await db.select().from(sellerAccounts).where(eq(sellerAccounts.id, accountId));
  if (!account) return null;

  const accountShops = await db.select().from(shops).where(eq(shops.sellerAccountId, accountId));
  const shopIds = accountShops.map((s) => s.id);

  let openCount = 0;
  let openOwedCents = 0;
  let recoveredCents = 0;
  let latestRunAt: Date | null = null;
  let topFindings: FindingRow[] = [];

  if (shopIds.length > 0) {
    const [openAgg] = await db
      .select({
        count: sql<number>`count(*)::int`,
        owed: sql<string>`coalesce(sum(case when ${discrepancies.delta} > 0 then ${discrepancies.delta} else 0 end), 0)`,
      })
      .from(discrepancies)
      .where(and(inArray(discrepancies.shopId, shopIds), eq(discrepancies.status, "open")));
    openCount = openAgg?.count ?? 0;
    openOwedCents = toCents(openAgg?.owed ?? "0");

    const [recoveredAgg] = await db
      .select({ recovered: sql<string>`coalesce(sum(${discrepancies.delta}), 0)` })
      .from(discrepancies)
      .where(and(inArray(discrepancies.shopId, shopIds), eq(discrepancies.status, "recovered")));
    recoveredCents = toCents(recoveredAgg?.recovered ?? "0");

    const [latestRun] = await db
      .select({ createdAt: reconciliationRuns.createdAt })
      .from(reconciliationRuns)
      .where(inArray(reconciliationRuns.shopId, shopIds))
      .orderBy(desc(reconciliationRuns.createdAt))
      .limit(1);
    latestRunAt = latestRun?.createdAt ?? null;

    const rows = await db
      .select()
      .from(discrepancies)
      .where(and(inArray(discrepancies.shopId, shopIds), eq(discrepancies.status, "open")))
      .orderBy(desc(discrepancies.delta))
      .limit(50);
    topFindings = rows.map((d) => ({
      id: d.id,
      checkId: d.checkId,
      orderId: d.ttsOrderId,
      feeType: d.feeType,
      deltaCents: toCents(d.delta),
      severity: d.severity,
      status: d.status,
    }));
  }

  return {
    email: account.email,
    plan: account.plan,
    planStatus: account.planStatus,
    shops: accountShops.map((s) => ({
      id: s.id,
      name: s.shopName,
      region: s.region,
      status: s.status,
      lastSyncedAt: s.lastSyncedAt,
    })),
    openCount,
    openOwedCents,
    recoveredCents,
    latestRunAt,
    topFindings,
  };
}

export interface ExportRow {
  checkId: string;
  orderId: string | null;
  skuId: string | null;
  feeType: string | null;
  expected: string | null;
  actual: string | null;
  delta: string | null;
  severity: string;
  status: string;
}

/** All discrepancies for an account's shops, for the evidence-pack export. */
export async function getDiscrepanciesForExport(accountId: string): Promise<ExportRow[]> {
  const db = getDb();
  const accountShops = await db
    .select({ id: shops.id })
    .from(shops)
    .where(eq(shops.sellerAccountId, accountId));
  const shopIds = accountShops.map((s) => s.id);
  if (shopIds.length === 0) return [];

  const rows = await db
    .select()
    .from(discrepancies)
    .where(inArray(discrepancies.shopId, shopIds))
    .orderBy(desc(discrepancies.delta));

  return rows.map((d) => ({
    checkId: d.checkId,
    orderId: d.ttsOrderId,
    skuId: d.skuId,
    feeType: d.feeType,
    expected: d.expectedAmount,
    actual: d.actualAmount,
    delta: d.delta,
    severity: d.severity,
    status: d.status,
  }));
}

/** Authorize that a discrepancy belongs to one of the account's shops. */
export async function discrepancyBelongsToAccount(
  discrepancyId: string,
  accountId: string,
): Promise<boolean> {
  const db = getDb();
  const [row] = await db
    .select({ shopId: discrepancies.shopId })
    .from(discrepancies)
    .where(eq(discrepancies.id, discrepancyId));
  if (!row?.shopId) return false;
  const [shop] = await db
    .select({ id: shops.id })
    .from(shops)
    .where(and(eq(shops.id, row.shopId), eq(shops.sellerAccountId, accountId)));
  return Boolean(shop);
}
