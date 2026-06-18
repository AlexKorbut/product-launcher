import * as XLSX from "xlsx";
import { toCents } from "../money";
import type { SettlementTransaction } from "../engine/types";
import { blankTransaction } from "./normalize";
import {
  buildColumnIndex,
  normalizeHeader,
  type ColumnSpec,
} from "./column-map";

export interface ParseResult {
  currency: string;
  transactions: SettlementTransaction[];
  /** headers we could not map — surfaced to the user AND logged for widening */
  unknownHeaders: string[];
  /** rows skipped because they had no order id */
  skippedRows: number;
  /** which target fields were actually populated from this file */
  mappedFields: string[];
}

export interface ParseOptions {
  /** default currency when the file carries none */
  defaultCurrency?: string;
  /** prefer a sheet whose name matches (case-insensitive contains) */
  preferSheet?: string;
}

/**
 * Parse a TikTok Seller Center settlement export (XLSX/CSV buffer) into
 * normalized transactions. Source-agnostic by design: the engine consumes the
 * same shape whether data arrives here or via the Finance API.
 */
export function parseSettlementWorkbook(
  data: ArrayBuffer | Uint8Array | Buffer,
  options: ParseOptions = {},
): ParseResult {
  const workbook = XLSX.read(data, { type: "array", cellDates: true });
  const sheetName = pickSheet(workbook, options.preferSheet);
  if (!sheetName) {
    return emptyResult(options.defaultCurrency);
  }
  const sheet = workbook.Sheets[sheetName]!;
  const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet, {
    defval: null,
    raw: true,
  });
  return parseRows(rows, options);
}

/** Exposed for unit tests and the API path that already has JSON rows. */
export function parseRows(
  rows: Record<string, unknown>[],
  options: ParseOptions = {},
): ParseResult {
  const index = buildColumnIndex();
  const currency = options.defaultCurrency ?? "USD";

  const unknownHeaders = new Set<string>();
  const mappedFields = new Set<string>();
  const transactions: SettlementTransaction[] = [];
  let skippedRows = 0;

  // Resolve each source header once to its spec (or mark unknown).
  const headerSpecs = new Map<string, ColumnSpec | null>();
  if (rows.length > 0) {
    for (const header of Object.keys(rows[0]!)) {
      const spec = index.get(normalizeHeader(header)) ?? null;
      headerSpecs.set(header, spec);
      if (!spec && !isIgnorableHeader(header)) unknownHeaders.add(header);
    }
  }

  for (const row of rows) {
    const draft: Partial<SettlementTransaction> & { orderId?: string } = {};
    let detectedCurrency: string | undefined;

    for (const [header, value] of Object.entries(row)) {
      const spec = headerSpecs.get(header);
      if (!spec || value === null || value === "") continue;
      applyCell(draft, spec, value, mappedFields);
      const cur = detectCurrencyFromHeader(header);
      if (cur) detectedCurrency = cur;
    }

    if (!draft.orderId) {
      skippedRows += 1;
      continue;
    }

    const tx = blankTransaction({
      ...draft,
      orderId: String(draft.orderId),
      currency: detectedCurrency ?? currency,
    });
    tx.type = inferType(tx);
    transactions.push(tx);
  }

  return {
    currency,
    transactions,
    unknownHeaders: [...unknownHeaders],
    skippedRows,
    mappedFields: [...mappedFields],
  };
}

function applyCell(
  draft: Record<string, unknown>,
  spec: ColumnSpec,
  value: unknown,
  mappedFields: Set<string>,
): void {
  if (spec.kind === "money") {
    let cents = toCents(value as string | number);
    if (spec.negate) cents = -cents;
    // Accumulate when several aliases map to the same field in one row.
    draft[spec.field] = ((draft[spec.field] as number) ?? 0) + cents;
  } else if (spec.kind === "date") {
    draft[spec.field] = toIsoDate(value);
  } else {
    draft[spec.field] = String(value).trim();
  }
  mappedFields.add(spec.field);
}

function inferType(tx: SettlementTransaction): SettlementTransaction["type"] {
  if (tx.grossSalesRefund < 0 || tx.customerRefund < 0 || tx.refundAdminFee !== 0) {
    return "refund";
  }
  if (tx.adjustmentId || (tx.adjustmentAmount !== 0 && tx.grossSales === 0 && tx.netSales === 0)) {
    return "adjustment";
  }
  return "order";
}

function pickSheet(
  workbook: XLSX.WorkBook,
  prefer?: string,
): string | undefined {
  const names = workbook.SheetNames;
  if (names.length === 0) return undefined;
  if (prefer) {
    const match = names.find((n) =>
      n.toLowerCase().includes(prefer.toLowerCase()),
    );
    if (match) return match;
  }
  // Prefer an order/transaction-level sheet over summary sheets.
  const preferred = names.find((n) =>
    /order|transaction|detail/i.test(n),
  );
  return preferred ?? names[0];
}

function isIgnorableHeader(header: string): boolean {
  const h = normalizeHeader(header);
  // Empty/auto-generated columns from xlsx (__EMPTY, __EMPTY_1, ...) and
  // descriptive columns we intentionally don't consume.
  return (
    h === "" ||
    header.startsWith("__EMPTY") ||
    /product name|currency|shop name|status|country|region|sku name|seller sku name/.test(h)
  );
}

function detectCurrencyFromHeader(header: string): string | undefined {
  const m = header.match(/\(([A-Z]{3})\)/);
  return m ? m[1] : undefined;
}

function toIsoDate(value: unknown): string | undefined {
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  if (typeof value === "number") {
    // Excel serial date
    const parsed = XLSX.SSF?.parse_date_code?.(value);
    if (parsed) {
      const mm = String(parsed.m).padStart(2, "0");
      const dd = String(parsed.d).padStart(2, "0");
      return `${parsed.y}-${mm}-${dd}`;
    }
  }
  const d = new Date(String(value));
  return Number.isNaN(d.getTime()) ? undefined : d.toISOString().slice(0, 10);
}

function emptyResult(currency?: string): ParseResult {
  return {
    currency: currency ?? "USD",
    transactions: [],
    unknownHeaders: [],
    skippedRows: 0,
    mappedFields: [],
  };
}
