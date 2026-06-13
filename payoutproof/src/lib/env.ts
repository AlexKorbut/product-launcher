/**
 * Central environment access. Reads are lazy so the app and tests can run
 * without every secret present; throw only when a feature actually needs one.
 */

function required(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function optional(name: string, fallback = ""): string {
  return process.env[name] ?? fallback;
}

export const env = {
  get databaseUrl() {
    return required("DATABASE_URL");
  },
  get appUrl() {
    return optional("APP_URL", "http://localhost:3000");
  },
  // TikTok Shop Open Platform
  get tiktokAppKey() {
    return required("TIKTOK_APP_KEY");
  },
  get tiktokAppSecret() {
    return required("TIKTOK_APP_SECRET");
  },
  get tiktokApiBase() {
    return optional("TIKTOK_API_BASE", "https://open-api.tiktokglobalshop.com");
  },
  get tiktokAuthBase() {
    return optional("TIKTOK_AUTH_BASE", "https://auth.tiktok-shops.com");
  },
  // Stripe
  get stripeSecretKey() {
    return required("STRIPE_SECRET_KEY");
  },
  get stripeWebhookSecret() {
    return required("STRIPE_WEBHOOK_SECRET");
  },
  // Token encryption key (32 bytes, base64)
  get encryptionKey() {
    return required("ENCRYPTION_KEY");
  },
  get resendApiKey() {
    return optional("RESEND_API_KEY");
  },
} as const;

export const STRIPE_PRICES: Record<string, { plan: string; priceEnv: string; monthlyOrderCap: number }> = {
  starter: { plan: "starter", priceEnv: "STRIPE_PRICE_STARTER", monthlyOrderCap: 500 },
  growth: { plan: "growth", priceEnv: "STRIPE_PRICE_GROWTH", monthlyOrderCap: 2500 },
  pro: { plan: "pro", priceEnv: "STRIPE_PRICE_PRO", monthlyOrderCap: 10000 },
  agency: { plan: "agency", priceEnv: "STRIPE_PRICE_AGENCY", monthlyOrderCap: Number.MAX_SAFE_INTEGER },
};
