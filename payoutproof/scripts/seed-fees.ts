import { getDb } from "../src/db";
import { feeSchedules } from "../src/db/schema";
import { SEED_FEE_SCHEDULE } from "../src/lib/engine/fee-schedule";

/** Seed the fee_schedules table from the in-code seed data. Idempotent-ish:
 *  clears and reinserts. Run with: tsx scripts/seed-fees.ts */
async function main() {
  const db = getDb();
  await db.delete(feeSchedules);
  await db.insert(feeSchedules).values(
    SEED_FEE_SCHEDULE.map((r) => ({
      region: r.region,
      feeType: r.feeType,
      category: r.category,
      rate: r.rate.toFixed(4),
      effectiveFrom: r.effectiveFrom,
      effectiveTo: r.effectiveTo,
      sourceUrl: r.sourceUrl,
    })),
  );
  console.log(`Seeded ${SEED_FEE_SCHEDULE.length} fee schedule rows.`);
  process.exit(0);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
