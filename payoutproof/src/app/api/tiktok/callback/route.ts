import { NextRequest, NextResponse } from "next/server";
import { eq } from "drizzle-orm";
import { makeTikTokClient } from "../../../../lib/tiktok/factory";
import { encryptToken } from "../../../../lib/crypto";
import { getDb } from "../../../../db";
import { sellerAccounts, shops } from "../../../../db/schema";
import { env } from "../../../../lib/env";

export const runtime = "nodejs";

/**
 * TikTok Shop OAuth callback. TikTok redirects here with ?code= and the
 * ?state we issued (carries the seller_account_id). We exchange the code,
 * enumerate authorized shops to capture each shop_cipher, and persist
 * encrypted tokens.
 */
export async function GET(req: NextRequest) {
  const code = req.nextUrl.searchParams.get("code");
  const state = req.nextUrl.searchParams.get("state");
  if (!code || !state) {
    return NextResponse.redirect(new URL("/app?connect=error", env.appUrl));
  }

  const sellerAccountId = state; // signed/opaque in production
  const client = makeTikTokClient();

  try {
    const db = getDb();
    const [account] = await db
      .select({ id: sellerAccounts.id })
      .from(sellerAccounts)
      .where(eq(sellerAccounts.id, sellerAccountId));
    if (!account) {
      return NextResponse.redirect(new URL("/login?error=expired", env.appUrl));
    }

    const token = await client.exchangeCode(code);
    const authorized = await client.getAuthorizedShops(token.access_token);

    for (const shop of authorized) {
      await db
        .insert(shops)
        .values({
          sellerAccountId,
          ttsShopId: shop.id,
          shopName: shop.name,
          shopCipher: shop.cipher,
          region: shop.region?.toUpperCase().startsWith("GB") ? "GB" : "US",
          accessTokenEnc: encryptToken(token.access_token),
          refreshTokenEnc: encryptToken(token.refresh_token),
          tokenExpiresAt: new Date(Date.now() + token.access_token_expire_in * 1000),
          status: "connected",
        })
        .onConflictDoUpdate({
          target: [shops.sellerAccountId, shops.ttsShopId],
          set: {
            shopCipher: shop.cipher,
            accessTokenEnc: encryptToken(token.access_token),
            refreshTokenEnc: encryptToken(token.refresh_token),
            tokenExpiresAt: new Date(Date.now() + token.access_token_expire_in * 1000),
            status: "connected",
          },
        });
    }

    return NextResponse.redirect(new URL("/app?connect=success", env.appUrl));
  } catch {
    return NextResponse.redirect(new URL("/app?connect=error", env.appUrl));
  }
}
