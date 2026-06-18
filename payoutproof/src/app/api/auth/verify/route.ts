import { NextRequest, NextResponse } from "next/server";
import { consumeMagicLink } from "../../../../lib/auth/magic-link";
import { setSession } from "../../../../lib/auth/session";

export const runtime = "nodejs";

/** Consume a magic-link token, establish a session, redirect to `next`. */
export async function GET(req: NextRequest) {
  const token = req.nextUrl.searchParams.get("token");
  const next = req.nextUrl.searchParams.get("next") ?? "/app";
  if (!token) {
    return NextResponse.redirect(new URL("/login?error=missing", req.url));
  }
  const result = await consumeMagicLink(token);
  if (!result) {
    return NextResponse.redirect(new URL("/login?error=expired", req.url));
  }
  await setSession({ accountId: result.accountId, email: result.email });
  const safeNext = next.startsWith("/") ? next : "/app";
  return NextResponse.redirect(new URL(safeNext, req.url));
}
