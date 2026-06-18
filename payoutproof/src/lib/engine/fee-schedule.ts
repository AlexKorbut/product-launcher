import type { Region } from "./types";

/**
 * Fee schedules are DATA, not code. TikTok changes rates; each row carries an
 * effective window. In production these rows live in the fee_schedules table
 * and are loaded per run; this module ships the seed data and the lookup so
 * the engine stays a pure function.
 *
 * Sources (verified June 2026):
 * - US referral fee: 6% of (customer payment + platform discount − sales tax)
 *   since July 2023 ramp; jewelry 5%; pre-Apr-2023 orders used a 1.8%/2%
 *   transaction fee instead.
 * - Refund administration fee: 20% of the referral fee is retained by TikTok
 *   on eligible refunds (i.e. 80% of the referral fee is returned).
 * - New-seller promo: 3% referral for first 30 days (post-Apr-2025 cohorts) —
 *   modeled as a shop_fee_override, not a schedule row.
 */

export interface FeeScheduleRow {
  region: Region;
  feeType: "referral" | "transaction";
  /** category key, or "*" for default */
  category: string;
  rate: number;
  effectiveFrom: string; // ISO date, inclusive
  effectiveTo?: string; // ISO date, exclusive
  sourceUrl?: string;
}

export interface ShopFeeOverride {
  feeType: "referral" | "transaction";
  rate: number;
  effectiveFrom: string;
  effectiveTo?: string;
  note?: string; // e.g. "new-seller 30-day promo"
}

export const SEED_FEE_SCHEDULE: FeeScheduleRow[] = [
  // US legacy transaction-fee era
  {
    region: "US",
    feeType: "transaction",
    category: "*",
    rate: 0.0,
    effectiveFrom: "2000-01-01",
    effectiveTo: "2023-04-01",
  },
  // US referral fee ramp: 2% → 6% during 2023; we seed the post-ramp rate and
  // the ramp window at its final announced steps.
  {
    region: "US",
    feeType: "referral",
    category: "*",
    rate: 0.02,
    effectiveFrom: "2023-04-01",
    effectiveTo: "2023-07-01",
  },
  {
    region: "US",
    feeType: "referral",
    category: "*",
    rate: 0.06,
    effectiveFrom: "2023-07-01",
  },
  {
    region: "US",
    feeType: "referral",
    category: "jewelry",
    rate: 0.05,
    effectiveFrom: "2023-07-01",
  },
  // UK
  {
    region: "GB",
    feeType: "referral",
    category: "*",
    rate: 0.05,
    effectiveFrom: "2023-07-01",
  },
];

/** Fraction of the referral fee TikTok keeps on an eligible refund. */
export const REFUND_ADMIN_RETENTION = 0.2;

export interface FeeLookup {
  referralRate(args: {
    region: Region;
    category?: string;
    orderDate?: string;
  }): number;
}

export function buildFeeLookup(
  schedule: FeeScheduleRow[] = SEED_FEE_SCHEDULE,
  overrides: ShopFeeOverride[] = [],
): FeeLookup {
  function findRate(
    feeType: "referral" | "transaction",
    region: Region,
    category: string,
    date: string,
  ): number | undefined {
    const within = (from: string, to?: string) => date >= from && (!to || date < to);
    const override = overrides.find(
      (o) => o.feeType === feeType && within(o.effectiveFrom, o.effectiveTo),
    );
    if (override) return override.rate;
    const exact = schedule.find(
      (r) =>
        r.feeType === feeType &&
        r.region === region &&
        r.category === category &&
        within(r.effectiveFrom, r.effectiveTo),
    );
    if (exact) return exact.rate;
    const fallback = schedule.find(
      (r) =>
        r.feeType === feeType &&
        r.region === region &&
        r.category === "*" &&
        within(r.effectiveFrom, r.effectiveTo),
    );
    return fallback?.rate;
  }

  return {
    referralRate({ region, category = "*", orderDate }) {
      const date = orderDate ?? new Date().toISOString().slice(0, 10);
      return findRate("referral", region, category.toLowerCase(), date) ?? 0.06;
    },
  };
}
