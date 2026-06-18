import { inArray, eq, and, sql } from "drizzle-orm";
import { getDb } from "../../db";
import { discrepancies, sellerAccounts, shops } from "../../db/schema";
import { sendEmail } from "../../lib/email";
import { formatCents } from "../../lib/money";

/**
 * Weekly digest: for each account with connected shops and open findings,
 * email a summary of money TikTok may owe them. This is the retention loop —
 * it pulls sellers back to act on (and recover) findings.
 */
export async function sendWeeklyDigests(): Promise<number> {
  const db = getDb();
  const accounts = await db.select().from(sellerAccounts);
  let sent = 0;

  for (const account of accounts) {
    const accountShops = await db
      .select({ id: shops.id })
      .from(shops)
      .where(eq(shops.sellerAccountId, account.id));
    const shopIds = accountShops.map((s) => s.id);
    if (shopIds.length === 0) continue;

    const [agg] = await db
      .select({
        count: sql<number>`count(*)::int`,
        owed: sql<string>`coalesce(sum(case when ${discrepancies.delta} > 0 then ${discrepancies.delta} else 0 end), 0)`,
      })
      .from(discrepancies)
      .where(and(inArray(discrepancies.shopId, shopIds), eq(discrepancies.status, "open")));

    const owedCents = agg?.owed ? Math.round(Number(agg.owed) * 100) : 0;
    const count = agg?.count ?? 0;
    if (count === 0 || owedCents <= 0) continue;

    await sendEmail({
      to: account.email,
      subject: `PayoutProof: ${formatCents(owedCents)} TikTok Shop may owe you`,
      html: `<p>This week's audit found <strong>${formatCents(owedCents)}</strong> across ${count} open findings on your TikTok Shop payouts.</p><p><a href="${process.env.APP_URL ?? ""}/app">Review and recover them →</a></p>`,
    });
    sent += 1;
  }
  return sent;
}
