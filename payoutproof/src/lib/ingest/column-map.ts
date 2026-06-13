import type { SettlementTransaction } from "../engine/types";

/**
 * TikTok Seller Center settlement exports are NOT a versioned, stable format —
 * column headers drift between regions and releases. We map by normalized
 * header (lowercased, punctuation-stripped) against a list of known aliases,
 * and emit telemetry for any header we don't recognize so the parser can be
 * widened before it silently drops money.
 */

export type NumericField = Exclude<
  {
    [K in keyof SettlementTransaction]: SettlementTransaction[K] extends number
      ? K
      : never;
  }[keyof SettlementTransaction],
  undefined
>;

export type StringField = "orderId" | "skuId" | "statementId" | "adjustmentId" | "adjustmentReason" | "statementDate" | "orderCreatedDate";

export interface ColumnSpec {
  field: NumericField | StringField;
  kind: "money" | "string" | "date";
  /** negate the parsed value (when source reports deductions as positive) */
  negate?: boolean;
  aliases: string[];
}

export function normalizeHeader(raw: string): string {
  return raw
    .toLowerCase()
    .replace(/\(.*?\)/g, " ") // strip parenthetical currency hints
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/**
 * Known column specs. Aliases are pre-normalized at match time, so list them
 * in human-readable form. Order matters only for documentation.
 */
export const COLUMN_SPECS: ColumnSpec[] = [
  { field: "orderId", kind: "string", aliases: ["order id", "order no", "order number", "related order id"] },
  { field: "skuId", kind: "string", aliases: ["sku id", "seller sku", "sku"] },
  { field: "statementId", kind: "string", aliases: ["statement id", "settlement id"] },
  { field: "adjustmentId", kind: "string", aliases: ["adjustment id", "adjustment order id"] },
  { field: "adjustmentReason", kind: "string", aliases: ["adjustment reason", "reason", "type of adjustment"] },
  { field: "statementDate", kind: "date", aliases: ["statement time", "statement date", "settlement time"] },
  { field: "orderCreatedDate", kind: "date", aliases: ["order created time", "order create time", "created time", "order time"] },

  { field: "grossSales", kind: "money", aliases: ["gross sales amount", "gross sales", "total revenue"] },
  { field: "netSales", kind: "money", aliases: ["net sales amount", "net sales"] },
  { field: "customerPayment", kind: "money", aliases: ["customer payment", "customer payment amount", "buyer paid amount"] },
  { field: "platformDiscount", kind: "money", aliases: ["platform discount amount", "platform discount"] },
  { field: "sellerDiscount", kind: "money", aliases: ["seller discount amount", "seller discount"] },
  { field: "salesTax", kind: "money", aliases: ["sales tax amount", "sales tax", "tax amount"] },

  { field: "referralFee", kind: "money", negate: false, aliases: ["referral fee amount", "referral fee", "platform commission amount", "commission fee"] },
  { field: "transactionFee", kind: "money", aliases: ["transaction fee amount", "transaction fee"] },
  { field: "refundAdminFee", kind: "money", aliases: ["refund administration fee amount", "refund administration fee", "refund admin fee"] },
  { field: "affiliateCommission", kind: "money", aliases: ["affiliate commission amount", "affiliate commission"] },
  { field: "affiliatePartnerCommission", kind: "money", aliases: ["affiliate partner commission amount", "affiliate partner commission"] },
  { field: "affiliateAdsCommission", kind: "money", aliases: ["affiliate ads commission amount", "affiliate shop ads commission amount", "affiliate ads commission"] },

  { field: "shippingActual", kind: "money", aliases: ["actual shipping fee amount", "actual shipping fee", "shipping cost amount"] },
  { field: "shippingCustomerPaid", kind: "money", aliases: ["customer paid shipping fee amount", "customer paid shipping fee"] },
  { field: "shippingSubsidy", kind: "money", aliases: ["shipping fee subsidy amount", "shipping fee subsidy", "platform shipping fee discount amount"] },
  { field: "fbtFees", kind: "money", aliases: ["fbt fulfillment fee amount", "fbt shipping cost amount", "fbt fee"] },

  { field: "adjustmentAmount", kind: "money", aliases: ["adjustment amount", "adjustment"] },
  { field: "grossSalesRefund", kind: "money", aliases: ["gross sales refund amount", "gross sales refund"] },
  { field: "customerRefund", kind: "money", aliases: ["customer refund amount", "customer refund", "total refund amount"] },

  { field: "settlementAmount", kind: "money", aliases: ["total settlement amount", "settlement amount", "net amount", "total amount"] },
];

/** Build a lookup from normalized alias -> spec. */
export function buildColumnIndex(): Map<string, ColumnSpec> {
  const index = new Map<string, ColumnSpec>();
  for (const spec of COLUMN_SPECS) {
    for (const alias of spec.aliases) {
      index.set(normalizeHeader(alias), spec);
    }
  }
  return index;
}
