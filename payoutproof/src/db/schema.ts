import {
  pgTable,
  uuid,
  text,
  timestamp,
  numeric,
  integer,
  jsonb,
  boolean,
  index,
  uniqueIndex,
} from "drizzle-orm/pg-core";

/**
 * Multi-tenant by seller_account_id on every owned row. Money columns are
 * numeric(14,4) + a currency column — never floats. API sync and XLSX upload
 * converge into the same statements / statement_transactions tables.
 */

export const sellerAccounts = pgTable("seller_accounts", {
  id: uuid("id").primaryKey().defaultRandom(),
  email: text("email").notNull().unique(),
  stripeCustomerId: text("stripe_customer_id"),
  plan: text("plan").notNull().default("free"), // free | starter | growth | pro | agency
  planStatus: text("plan_status").notNull().default("inactive"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const shops = pgTable(
  "shops",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    sellerAccountId: uuid("seller_account_id")
      .notNull()
      .references(() => sellerAccounts.id, { onDelete: "cascade" }),
    ttsShopId: text("tts_shop_id").notNull(),
    shopName: text("shop_name"),
    shopCipher: text("shop_cipher"),
    region: text("region").notNull().default("US"), // US | GB
    category: text("category"),
    accessTokenEnc: text("access_token_enc"),
    refreshTokenEnc: text("refresh_token_enc"),
    tokenExpiresAt: timestamp("token_expires_at", { withTimezone: true }),
    status: text("status").notNull().default("disconnected"),
    lastSyncedAt: timestamp("last_synced_at", { withTimezone: true }),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => ({
    byAccount: index("shops_account_idx").on(t.sellerAccountId),
    uniqueShop: uniqueIndex("shops_account_tts_uidx").on(t.sellerAccountId, t.ttsShopId),
  }),
);

export const statements = pgTable(
  "statements",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    shopId: uuid("shop_id")
      .notNull()
      .references(() => shops.id, { onDelete: "cascade" }),
    ttsStatementId: text("tts_statement_id").notNull(),
    statementTime: timestamp("statement_time", { withTimezone: true }),
    currency: text("currency").notNull().default("USD"),
    settlementAmount: numeric("settlement_amount", { precision: 14, scale: 4 }),
    revenueAmount: numeric("revenue_amount", { precision: 14, scale: 4 }),
    feeAmount: numeric("fee_amount", { precision: 14, scale: 4 }),
    shippingCostAmount: numeric("shipping_cost_amount", { precision: 14, scale: 4 }),
    adjustmentAmount: numeric("adjustment_amount", { precision: 14, scale: 4 }),
    paymentId: text("payment_id"),
    source: text("source").notNull().default("upload"), // api | upload
    raw: jsonb("raw"),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => ({
    byShop: index("statements_shop_idx").on(t.shopId),
    uniqueStatement: uniqueIndex("statements_shop_tts_uidx").on(t.shopId, t.ttsStatementId),
  }),
);

export const statementTransactions = pgTable(
  "statement_transactions",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    statementId: uuid("statement_id").references(() => statements.id, { onDelete: "cascade" }),
    shopId: uuid("shop_id")
      .notNull()
      .references(() => shops.id, { onDelete: "cascade" }),
    ttsOrderId: text("tts_order_id").notNull(),
    skuId: text("sku_id"),
    type: text("type").notNull().default("order"),
    currency: text("currency").notNull().default("USD"),
    // money columns mirror SettlementTransaction; stored in major units
    grossSales: numeric("gross_sales", { precision: 14, scale: 4 }),
    netSales: numeric("net_sales", { precision: 14, scale: 4 }),
    customerPayment: numeric("customer_payment", { precision: 14, scale: 4 }),
    salesTax: numeric("sales_tax", { precision: 14, scale: 4 }),
    referralFee: numeric("referral_fee", { precision: 14, scale: 4 }),
    transactionFee: numeric("transaction_fee", { precision: 14, scale: 4 }),
    refundAdminFee: numeric("refund_admin_fee", { precision: 14, scale: 4 }),
    affiliateCommission: numeric("affiliate_commission", { precision: 14, scale: 4 }),
    shippingActual: numeric("shipping_actual", { precision: 14, scale: 4 }),
    fbtFees: numeric("fbt_fees", { precision: 14, scale: 4 }),
    adjustmentAmount: numeric("adjustment_amount", { precision: 14, scale: 4 }),
    adjustmentId: text("adjustment_id"),
    settlementAmount: numeric("settlement_amount", { precision: 14, scale: 4 }),
    orderCreatedDate: text("order_created_date"),
    raw: jsonb("raw"),
  },
  (t) => ({
    byShop: index("stmt_tx_shop_idx").on(t.shopId),
    uniqueTx: uniqueIndex("stmt_tx_uidx").on(
      t.shopId,
      t.ttsOrderId,
      t.skuId,
      t.type,
    ),
  }),
);

export const uploads = pgTable("uploads", {
  id: uuid("id").primaryKey().defaultRandom(),
  sellerAccountId: uuid("seller_account_id").references(() => sellerAccounts.id, {
    onDelete: "cascade",
  }),
  shopId: uuid("shop_id").references(() => shops.id, { onDelete: "set null" }),
  filename: text("filename"),
  parsedRows: integer("parsed_rows").notNull().default(0),
  skippedRows: integer("skipped_rows").notNull().default(0),
  unknownHeaders: jsonb("unknown_headers"),
  status: text("status").notNull().default("parsed"),
  email: text("email"), // captured by the free tool's email gate
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const feeSchedules = pgTable("fee_schedules", {
  id: uuid("id").primaryKey().defaultRandom(),
  region: text("region").notNull(),
  feeType: text("fee_type").notNull(),
  category: text("category").notNull().default("*"),
  rate: numeric("rate", { precision: 6, scale: 4 }).notNull(),
  effectiveFrom: text("effective_from").notNull(),
  effectiveTo: text("effective_to"),
  sourceUrl: text("source_url"),
});

export const shopFeeOverrides = pgTable("shop_fee_overrides", {
  id: uuid("id").primaryKey().defaultRandom(),
  shopId: uuid("shop_id")
    .notNull()
    .references(() => shops.id, { onDelete: "cascade" }),
  feeType: text("fee_type").notNull(),
  rate: numeric("rate", { precision: 6, scale: 4 }).notNull(),
  effectiveFrom: text("effective_from").notNull(),
  effectiveTo: text("effective_to"),
  note: text("note"),
});

export const reconciliationRuns = pgTable("reconciliation_runs", {
  id: uuid("id").primaryKey().defaultRandom(),
  shopId: uuid("shop_id").references(() => shops.id, { onDelete: "cascade" }),
  uploadId: uuid("upload_id").references(() => uploads.id, { onDelete: "set null" }),
  engineVersion: text("engine_version").notNull(),
  feeScheduleSnapshot: jsonb("fee_schedule_snapshot"),
  totalOwed: numeric("total_owed", { precision: 14, scale: 4 }),
  totals: jsonb("totals"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const discrepancies = pgTable(
  "discrepancies",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    runId: uuid("run_id")
      .notNull()
      .references(() => reconciliationRuns.id, { onDelete: "cascade" }),
    shopId: uuid("shop_id").references(() => shops.id, { onDelete: "cascade" }),
    checkId: text("check_id").notNull(),
    ttsOrderId: text("tts_order_id"),
    skuId: text("sku_id"),
    feeType: text("fee_type"),
    expectedAmount: numeric("expected_amount", { precision: 14, scale: 4 }),
    actualAmount: numeric("actual_amount", { precision: 14, scale: 4 }),
    delta: numeric("delta", { precision: 14, scale: 4 }),
    severity: text("severity").notNull().default("info"),
    status: text("status").notNull().default("open"), // open|explained|recovered|dismissed
    explanation: text("explanation"),
    context: jsonb("context"),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => ({
    byRun: index("discrepancies_run_idx").on(t.runId),
    byStatus: index("discrepancies_status_idx").on(t.status),
  }),
);

export const subscriptions = pgTable("subscriptions", {
  id: uuid("id").primaryKey().defaultRandom(),
  sellerAccountId: uuid("seller_account_id")
    .notNull()
    .references(() => sellerAccounts.id, { onDelete: "cascade" }),
  stripeSubscriptionId: text("stripe_subscription_id").unique(),
  stripePriceId: text("stripe_price_id"),
  plan: text("plan").notNull(),
  status: text("status").notNull(),
  currentPeriodEnd: timestamp("current_period_end", { withTimezone: true }),
  cancelAtPeriodEnd: boolean("cancel_at_period_end").notNull().default(false),
});
