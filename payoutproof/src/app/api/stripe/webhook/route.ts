import { NextRequest, NextResponse } from "next/server";
import type Stripe from "stripe";
import { getStripe } from "../../../../lib/billing/stripe";
import { env, STRIPE_PRICES } from "../../../../lib/env";
import { getDb } from "../../../../db";
import { sellerAccounts, subscriptions } from "../../../../db/schema";
import { eq } from "drizzle-orm";

export const runtime = "nodejs";

/** Stripe needs the raw body to verify the signature. */
export async function POST(req: NextRequest) {
  const sig = req.headers.get("stripe-signature");
  if (!sig) return NextResponse.json({ error: "missing signature" }, { status: 400 });

  const raw = await req.text();
  let event: Stripe.Event;
  try {
    event = getStripe().webhooks.constructEvent(raw, sig, env.stripeWebhookSecret);
  } catch (err) {
    const msg = err instanceof Error ? err.message : "invalid";
    return NextResponse.json({ error: `Webhook signature failed: ${msg}` }, { status: 400 });
  }

  const db = getDb();

  switch (event.type) {
    case "checkout.session.completed": {
      const session = event.data.object as Stripe.Checkout.Session;
      const sellerAccountId = session.metadata?.sellerAccountId ?? session.client_reference_id;
      if (sellerAccountId && session.customer) {
        await db
          .update(sellerAccounts)
          .set({ stripeCustomerId: String(session.customer), planStatus: "trialing" })
          .where(eq(sellerAccounts.id, sellerAccountId));
      }
      break;
    }
    case "customer.subscription.created":
    case "customer.subscription.updated":
    case "customer.subscription.deleted": {
      const sub = event.data.object as Stripe.Subscription;
      const priceId = sub.items.data[0]?.price.id;
      const plan = planForPriceId(priceId) ?? "growth";
      const customerId = String(sub.customer);

      const [account] = await db
        .select()
        .from(sellerAccounts)
        .where(eq(sellerAccounts.stripeCustomerId, customerId));

      if (account) {
        await db
          .insert(subscriptions)
          .values({
            sellerAccountId: account.id,
            stripeSubscriptionId: sub.id,
            stripePriceId: priceId,
            plan,
            status: sub.status,
            cancelAtPeriodEnd: sub.cancel_at_period_end ?? false,
          })
          .onConflictDoUpdate({
            target: subscriptions.stripeSubscriptionId,
            set: { status: sub.status, plan, cancelAtPeriodEnd: sub.cancel_at_period_end ?? false },
          });

        const active = sub.status === "active" || sub.status === "trialing";
        await db
          .update(sellerAccounts)
          .set({ plan: active ? plan : "free", planStatus: sub.status })
          .where(eq(sellerAccounts.id, account.id));
      }
      break;
    }
    default:
      break;
  }

  return NextResponse.json({ received: true });
}

function planForPriceId(priceId?: string): string | undefined {
  if (!priceId) return undefined;
  for (const [, spec] of Object.entries(STRIPE_PRICES)) {
    if (process.env[spec.priceEnv] === priceId) return spec.plan;
  }
  return undefined;
}
