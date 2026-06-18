import { createCipheriv, createDecipheriv, randomBytes } from "node:crypto";
import { env } from "./env";

/**
 * Authenticated encryption for TikTok access/refresh tokens at rest.
 * AES-256-GCM; key is 32 bytes base64 in ENCRYPTION_KEY. Stored format:
 * base64(iv).base64(authTag).base64(ciphertext)
 */
function key(): Buffer {
  const k = Buffer.from(env.encryptionKey, "base64");
  if (k.length !== 32) {
    throw new Error("ENCRYPTION_KEY must be 32 bytes (base64-encoded)");
  }
  return k;
}

export function encryptToken(plaintext: string): string {
  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", key(), iv);
  const ct = Buffer.concat([cipher.update(plaintext, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return [iv.toString("base64"), tag.toString("base64"), ct.toString("base64")].join(".");
}

export function decryptToken(payload: string): string {
  const [ivB64, tagB64, ctB64] = payload.split(".");
  if (!ivB64 || !tagB64 || !ctB64) throw new Error("Malformed encrypted token");
  const decipher = createDecipheriv("aes-256-gcm", key(), Buffer.from(ivB64, "base64"));
  decipher.setAuthTag(Buffer.from(tagB64, "base64"));
  return Buffer.concat([
    decipher.update(Buffer.from(ctB64, "base64")),
    decipher.final(),
  ]).toString("utf8");
}
