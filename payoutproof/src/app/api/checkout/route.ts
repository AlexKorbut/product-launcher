import { NextRequest, NextResponse } from "next/server";
import { createCheckoutSession } from "../../../lib/billing/stripe";
import { getDb } from "../../../db";
import { sellerAccounts } from "../../../db/schema";
import { eq } from "drizzle-orm";

export const runtime = "nodejs";

/**
 * Start a Stripe Checkout session for a plan. In production the seller's email
 * comes from the authenticated session; here we accept it from the form for
 * the trial flow and upsert a seller account.
 */
export async function POST(req: NextRequest) {
  const form = await req.formData();
  const plan = String(form.get("plan") ?? "growth");
  const email = form.get("email") ? String(form.get("email")) : undefined;

  if (!email) {
    // No session yet — bounce to a signup page that collects email then returns.
    return NextResponse.redirect(new URL(`/signup?plan=${plan}`, req.url), 303);
  }

  const db = getDb();
  let [account] = await db.select().from(sellerAccounts).where(eq(sellerAccounts.email, email));
  if (!account) {
    [account] = await db.insert(sellerAccounts).values({ email }).returning();
  }

  const url = await createCheckoutSession({
    plan,
    customerEmail: email,
    sellerAccountId: account!.id,
  });
  return NextResponse.redirect(url, 303);
}
