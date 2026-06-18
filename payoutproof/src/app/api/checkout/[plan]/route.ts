import { NextRequest, NextResponse } from "next/server";
import { createCheckoutSession } from "../../../../lib/billing/stripe";
import { getSession } from "../../../../lib/auth/session";
import { STRIPE_PRICES } from "../../../../lib/env";

export const runtime = "nodejs";

/**
 * Start Stripe Checkout for a plan. Requires a session; if absent, bounce
 * through magic-link login and return here afterwards.
 */
export async function GET(req: NextRequest, ctx: { params: Promise<{ plan: string }> }) {
  const { plan } = await ctx.params;
  if (!STRIPE_PRICES[plan]) {
    return NextResponse.redirect(new URL("/pricing?error=plan", req.url), 303);
  }

  const session = await getSession();
  if (!session) {
    const next = encodeURIComponent(`/api/checkout/${plan}`);
    return NextResponse.redirect(new URL(`/login?next=${next}`, req.url), 303);
  }

  try {
    const url = await createCheckoutSession({
      plan,
      customerEmail: session.email,
      sellerAccountId: session.accountId,
    });
    return NextResponse.redirect(url, 303);
  } catch (err) {
    console.error("[checkout]", err);
    return NextResponse.redirect(new URL("/pricing?error=stripe", req.url), 303);
  }
}
