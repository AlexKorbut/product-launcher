import { NextRequest, NextResponse } from "next/server";
import { buildAuthUrl } from "../../../../lib/tiktok/factory";

export const runtime = "nodejs";

/**
 * Begin TikTok Shop OAuth. In production `state` is a signed token bound to the
 * authenticated seller account; here it is read from a query param for the
 * connect button and should be replaced with the session account id.
 */
export async function GET(req: NextRequest) {
  const sellerAccountId = req.nextUrl.searchParams.get("account") ?? "pending";
  return NextResponse.redirect(buildAuthUrl(sellerAccountId));
}
