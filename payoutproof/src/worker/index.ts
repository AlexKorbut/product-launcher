import PgBoss from "pg-boss";
import { getDb } from "../db";
import { shops } from "../db/schema";
import { eq } from "drizzle-orm";
import { env } from "../lib/env";
import { syncShop, type SyncShopPayload } from "./jobs/sync-shop";

/**
 * Single always-on worker process. pg-boss stores its queue in the same
 * Postgres database, so there is no Redis or extra infrastructure.
 *
 * - `sync-shop` runs the API pull + reconciliation for one shop.
 * - `enqueue-due-shops` is a scheduled fan-out that queues every connected
 *   shop on an interval.
 */
const SYNC_QUEUE = "sync-shop";
const SCHEDULE_QUEUE = "enqueue-due-shops";

async function main() {
  const boss = new PgBoss({ connectionString: env.databaseUrl });
  boss.on("error", (err) => console.error("[pg-boss]", err));
  await boss.start();

  await boss.createQueue(SYNC_QUEUE);
  await boss.createQueue(SCHEDULE_QUEUE);

  await boss.work<SyncShopPayload>(SYNC_QUEUE, { batchSize: 1 }, async ([job]) => {
    if (!job) return;
    console.log(`[sync-shop] ${job.data.shopId}`);
    await syncShop(job.data);
  });

  await boss.work(SCHEDULE_QUEUE, async () => {
    const db = getDb();
    const connected = await db.select().from(shops).where(eq(shops.status, "connected"));
    for (const shop of connected) {
      await boss.send(SYNC_QUEUE, { shopId: shop.id });
    }
    console.log(`[scheduler] enqueued ${connected.length} shops`);
  });

  // Fan out every 8 hours.
  await boss.schedule(SCHEDULE_QUEUE, "0 */8 * * *");

  console.log("PayoutProof worker started.");
}

main().catch((err) => {
  console.error("Worker failed to start:", err);
  process.exit(1);
});
