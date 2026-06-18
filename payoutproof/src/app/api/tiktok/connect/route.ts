import { NextResponse } from "next/server";
import { buildAuthUrl } from "../../../../lib/tiktok/factory";
import { getSession } from "../../../../lib/auth/session";

export const runtime = "nodejs";

/**
 * Begin TikTok Shop OAuth. `state` is bound to the authenticated seller
 * account so the callback can attribute the connected shop. Requires a session.
 */
export async function GET() {
  const session = await getSession();
  if (!session) {
    return NextResponse.redirect(`${process.env.APP_URL ?? "http://localhost:3000"}/login?next=/api/tiktok/connect`);
  }
  return NextResponse.redirect(buildAuthUrl(session.accountId));
}
