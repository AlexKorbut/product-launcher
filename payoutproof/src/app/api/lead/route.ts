import { NextRequest, NextResponse } from "next/server";
import { getDb } from "../../../db";
import { uploads } from "../../../db/schema";

export const runtime = "nodejs";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Capture a free-tool lead: store the email plus the audit summary so we can
 * follow up ("we found $X across your statements — automate this"). This is
 * the lead magnet's conversion hook.
 */
export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const email = String(body.email ?? "").trim().toLowerCase();
  if (!EMAIL_RE.test(email)) {
    return NextResponse.json({ error: "invalid email" }, { status: 400 });
  }

  try {
    const db = getDb();
    await db.insert(uploads).values({
      email,
      filename: body.filename ? String(body.filename) : "free-tool-audit",
      parsedRows: Number.isFinite(body.rows) ? Math.trunc(body.rows) : 0,
      status: "lead",
      unknownHeaders: { owedCents: body.owedCents ?? 0 },
    });
  } catch (err) {
    console.error("[lead]", err);
    // Don't block the UX on a storage hiccup.
  }

  return NextResponse.json({ ok: true });
}
