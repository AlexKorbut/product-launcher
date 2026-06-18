import { createHmac } from "node:crypto";

/**
 * TikTok Shop Open Platform request signing (v2 / 202xx APIs).
 *
 * Algorithm (per the official "Signing requests" guide):
 *  1. Collect all query params EXCEPT `sign` and `access_token`.
 *  2. Sort the keys alphabetically.
 *  3. Build base = path, then for each sorted key append `${key}${value}`.
 *  4. If a JSON request body is present (non-multipart), append the raw body.
 *  5. Wrap: `${appSecret}${base}${appSecret}`.
 *  6. HMAC-SHA256 with appSecret, hex digest (lowercase).
 */
export function signRequest(args: {
  appSecret: string;
  path: string;
  query: Record<string, string | number | undefined>;
  body?: string;
}): string {
  const { appSecret, path, query, body } = args;

  const entries = Object.entries(query)
    .filter(([k, v]) => k !== "sign" && k !== "access_token" && v !== undefined && v !== "")
    .map(([k, v]) => [k, String(v)] as const)
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));

  let base = path;
  for (const [k, v] of entries) {
    base += `${k}${v}`;
  }
  if (body && body.length > 0) {
    base += body;
  }

  const wrapped = `${appSecret}${base}${appSecret}`;
  return createHmac("sha256", appSecret).update(wrapped, "utf8").digest("hex");
}
