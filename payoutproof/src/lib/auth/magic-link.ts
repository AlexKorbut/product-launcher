import { createHash, randomBytes } from "node:crypto";
import { and, eq, gt, isNull } from "drizzle-orm";
import { getDb } from "../../db";
import { authTokens, sellerAccounts } from "../../db/schema";
import { env } from "../env";

const TOKEN_TTL_MS = 1000 * 60 * 30; // 30 minutes

function hashToken(raw: string): string {
  return createHash("sha256").update(raw).digest("hex");
}

/**
 * Create a single-use login token, store only its hash, and return the magic
 * link URL. The raw token lives only in the emailed URL.
 */
export async function createMagicLink(email: string): Promise<string> {
  const normalized = email.trim().toLowerCase();
  const raw = randomBytes(32).toString("base64url");
  const db = getDb();
  await db.insert(authTokens).values({
    email: normalized,
    tokenHash: hashToken(raw),
    purpose: "login",
    expiresAt: new Date(Date.now() + TOKEN_TTL_MS),
  });
  const url = new URL("/api/auth/verify", env.appUrl);
  url.searchParams.set("token", raw);
  return url.toString();
}

export interface VerifyResult {
  accountId: string;
  email: string;
}

/**
 * Consume a magic-link token: validate hash, check not expired/consumed, mark
 * consumed, and upsert the seller account. Returns null on any failure.
 */
export async function consumeMagicLink(raw: string): Promise<VerifyResult | null> {
  const db = getDb();
  const tokenHash = hashToken(raw);
  const [row] = await db
    .select()
    .from(authTokens)
    .where(
      and(
        eq(authTokens.tokenHash, tokenHash),
        isNull(authTokens.consumedAt),
        gt(authTokens.expiresAt, new Date()),
      ),
    );
  if (!row) return null;

  await db.update(authTokens).set({ consumedAt: new Date() }).where(eq(authTokens.id, row.id));

  let [account] = await db
    .select()
    .from(sellerAccounts)
    .where(eq(sellerAccounts.email, row.email));
  if (!account) {
    [account] = await db.insert(sellerAccounts).values({ email: row.email }).returning();
  }
  return { accountId: account!.id, email: account!.email };
}
