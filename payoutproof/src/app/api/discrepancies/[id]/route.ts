import { NextRequest, NextResponse } from "next/server";
import { eq } from "drizzle-orm";
import { getSession } from "../../../../lib/auth/session";
import { discrepancyBelongsToAccount } from "../../../../lib/services/account-queries";
import { getDb } from "../../../../db";
import { discrepancies } from "../../../../db/schema";

export const runtime = "nodejs";

const VALID_STATUSES = new Set(["open", "explained", "recovered", "dismissed"]);

/** Update a finding's status (the recovery workflow). Owner-scoped. */
export async function PATCH(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const { id } = await ctx.params;
  const body = await req.json().catch(() => ({}));
  const status = String(body.status ?? "");
  if (!VALID_STATUSES.has(status)) {
    return NextResponse.json({ error: "invalid status" }, { status: 400 });
  }

  const owned = await discrepancyBelongsToAccount(id, session.accountId);
  if (!owned) return NextResponse.json({ error: "not found" }, { status: 404 });

  const db = getDb();
  await db
    .update(discrepancies)
    .set({ status, explanation: body.explanation ? String(body.explanation) : undefined })
    .where(eq(discrepancies.id, id));

  return NextResponse.json({ ok: true, id, status });
}
