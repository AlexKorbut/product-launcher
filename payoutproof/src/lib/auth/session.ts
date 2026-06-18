import { createHmac, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";
import { env } from "../env";

/**
 * Stateless signed-cookie sessions. The cookie payload is
 * base64url(json).base64url(hmacSHA256). No server-side session store needed;
 * revocation is by short TTL. httpOnly + secure in production.
 */

const COOKIE_NAME = "pp_session";
const TTL_SECONDS = 60 * 60 * 24 * 30; // 30 days

export interface SessionData {
  accountId: string;
  email: string;
  /** issued-at, unix seconds */
  iat: number;
}

function b64url(input: Buffer | string): string {
  return Buffer.from(input).toString("base64url");
}

function sign(payload: string): string {
  return createHmac("sha256", env.sessionSecret).update(payload).digest("base64url");
}

export function encodeSession(data: Omit<SessionData, "iat">): string {
  const full: SessionData = { ...data, iat: Math.floor(Date.now() / 1000) };
  const payload = b64url(JSON.stringify(full));
  return `${payload}.${sign(payload)}`;
}

export function decodeSession(token: string | undefined): SessionData | null {
  if (!token) return null;
  const [payload, mac] = token.split(".");
  if (!payload || !mac) return null;
  const expected = sign(payload);
  const a = Buffer.from(mac);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !timingSafeEqual(a, b)) return null;
  try {
    const data = JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as SessionData;
    if (!data.iat || Date.now() / 1000 - data.iat > TTL_SECONDS) return null;
    return data;
  } catch {
    return null;
  }
}

/** Server-side: read the current session from the request cookies. */
export async function getSession(): Promise<SessionData | null> {
  const store = await cookies();
  return decodeSession(store.get(COOKIE_NAME)?.value);
}

export async function setSession(data: Omit<SessionData, "iat">): Promise<void> {
  const store = await cookies();
  store.set(COOKIE_NAME, encodeSession(data), {
    httpOnly: true,
    secure: env.isProduction,
    sameSite: "lax",
    path: "/",
    maxAge: TTL_SECONDS,
  });
}

export async function clearSession(): Promise<void> {
  const store = await cookies();
  store.delete(COOKIE_NAME);
}

export { COOKIE_NAME };
