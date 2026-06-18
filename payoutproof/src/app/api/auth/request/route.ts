import { NextRequest, NextResponse } from "next/server";
import { createMagicLink } from "../../../../lib/auth/magic-link";
import { sendEmail, magicLinkEmail } from "../../../../lib/email";

export const runtime = "nodejs";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** Accepts an email, sends a magic sign-in link. Always returns success to
 *  avoid leaking which emails have accounts. */
export async function POST(req: NextRequest) {
  const form = await req.formData().catch(() => null);
  const email = String(form?.get("email") ?? req.nextUrl.searchParams.get("email") ?? "").trim();
  const next = String(form?.get("next") ?? "/app");

  if (!EMAIL_RE.test(email)) {
    return NextResponse.redirect(new URL(`/login?error=invalid`, req.url), 303);
  }

  try {
    const url = await createMagicLink(email);
    const withNext = new URL(url);
    withNext.searchParams.set("next", next);
    const tmpl = magicLinkEmail(withNext.toString());
    await sendEmail({ to: email, ...tmpl });
  } catch (err) {
    console.error("[auth/request]", err);
  }

  return NextResponse.redirect(new URL(`/login?sent=1`, req.url), 303);
}
