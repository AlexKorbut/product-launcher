import { TikTokShopClient } from "./client";
import { env } from "../env";

/** Build a configured TikTok client from environment. */
export function makeTikTokClient(): TikTokShopClient {
  return new TikTokShopClient({
    appKey: env.tiktokAppKey,
    appSecret: env.tiktokAppSecret,
    apiBase: env.tiktokApiBase,
    authBase: env.tiktokAuthBase,
  });
}

/** The seller-facing authorization URL to begin OAuth. */
export function buildAuthUrl(state: string): string {
  const url = new URL("https://services.tiktokshop.com/open/authorize");
  url.searchParams.set("app_key", env.tiktokAppKey);
  url.searchParams.set("state", state);
  return url.toString();
}
