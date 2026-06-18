import Stripe from "stripe";
import { env, STRIPE_PRICES } from "../env";

let stripe: Stripe | undefined;

export function getStripe(): Stripe {
  if (!stripe) {
    stripe = new Stripe(env.stripeSecretKey, { apiVersion: "2025-08-27.basil" });
  }
  return stripe;
}

export function priceIdForPlan(plan: string): string {
  const spec = STRIPE_PRICES[plan];
  if (!spec) throw new Error(`Unknown plan: ${plan}`);
  const priceId = process.env[spec.priceEnv];
  if (!priceId) throw new Error(`Missing price env ${spec.priceEnv} for plan ${plan}`);
  return priceId;
}

export async function createCheckoutSession(args: {
  plan: string;
  customerEmail: string;
  sellerAccountId: string;
}): Promise<string> {
  const session = await getStripe().checkout.sessions.create({
    mode: "subscription",
    customer_email: args.customerEmail,
    line_items: [{ price: priceIdForPlan(args.plan), quantity: 1 }],
    subscription_data: { trial_period_days: 14 },
    client_reference_id: args.sellerAccountId,
    metadata: { sellerAccountId: args.sellerAccountId, plan: args.plan },
    success_url: `${env.appUrl}/app?checkout=success`,
    cancel_url: `${env.appUrl}/pricing?checkout=cancelled`,
  });
  if (!session.url) throw new Error("Stripe did not return a checkout URL");
  return session.url;
}

export async function createBillingPortalSession(customerId: string): Promise<string> {
  const session = await getStripe().billingPortal.sessions.create({
    customer: customerId,
    return_url: `${env.appUrl}/app`,
  });
  return session.url;
}
