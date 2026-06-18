/**
 * All monetary amounts flow through the system as integer cents.
 * Source data (TikTok API JSON, Seller Center XLSX) carries decimal strings
 * or floats; convert at the ingestion boundary and never do float math after.
 */

export type Cents = number;

/** Parse a decimal amount (string | number) into integer cents. */
export function toCents(value: string | number | null | undefined): Cents {
  if (value === null || value === undefined || value === "") return 0;
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new Error(`Non-finite monetary value: ${value}`);
    }
    return Math.round(value * 100);
  }
  // Strings: strip currency symbols, thousands separators, surrounding space.
  // Accounting-style negatives "(1.23)" mean -1.23.
  let s = value.trim();
  const parenNegative = /^\(.*\)$/.test(s);
  if (parenNegative) s = s.slice(1, -1);
  s = s.replace(/[$£€,\s]/g, "");
  if (s === "" || s === "-") return 0;
  const n = Number(s);
  if (!Number.isFinite(n)) {
    throw new Error(`Unparseable monetary value: ${JSON.stringify(value)}`);
  }
  const cents = Math.round(n * 100);
  return parenNegative ? -cents : cents;
}

export function formatCents(cents: Cents, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(
    cents / 100,
  );
}

/** Round half-away-from-zero, the convention marketplace fee tables use. */
export function roundHalfAwayFromZero(value: number): number {
  return Math.sign(value) * Math.round(Math.abs(value));
}

/** expected fee in cents for a rate (e.g. 0.06) applied to a cents base */
export function applyRate(baseCents: Cents, rate: number): Cents {
  return roundHalfAwayFromZero(baseCents * rate);
}
