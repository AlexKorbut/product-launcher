import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

/** Legacy POST entrypoint: normalize to the session-aware GET flow. */
export async function POST(req: NextRequest) {
  const form = await req.formData().catch(() => null);
  const plan = String(form?.get("plan") ?? "growth");
  return NextResponse.redirect(new URL(`/api/checkout/${plan}`, req.url), 303);
}
