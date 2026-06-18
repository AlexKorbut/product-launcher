CREATE TABLE "discrepancies" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"run_id" uuid NOT NULL,
	"shop_id" uuid,
	"check_id" text NOT NULL,
	"tts_order_id" text,
	"sku_id" text,
	"fee_type" text,
	"expected_amount" numeric(14, 4),
	"actual_amount" numeric(14, 4),
	"delta" numeric(14, 4),
	"severity" text DEFAULT 'info' NOT NULL,
	"status" text DEFAULT 'open' NOT NULL,
	"explanation" text,
	"context" jsonb,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "fee_schedules" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"region" text NOT NULL,
	"fee_type" text NOT NULL,
	"category" text DEFAULT '*' NOT NULL,
	"rate" numeric(6, 4) NOT NULL,
	"effective_from" text NOT NULL,
	"effective_to" text,
	"source_url" text
);
--> statement-breakpoint
CREATE TABLE "reconciliation_runs" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"shop_id" uuid,
	"upload_id" uuid,
	"engine_version" text NOT NULL,
	"fee_schedule_snapshot" jsonb,
	"total_owed" numeric(14, 4),
	"totals" jsonb,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "seller_accounts" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"email" text NOT NULL,
	"stripe_customer_id" text,
	"plan" text DEFAULT 'free' NOT NULL,
	"plan_status" text DEFAULT 'inactive' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "seller_accounts_email_unique" UNIQUE("email")
);
--> statement-breakpoint
CREATE TABLE "shop_fee_overrides" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"shop_id" uuid NOT NULL,
	"fee_type" text NOT NULL,
	"rate" numeric(6, 4) NOT NULL,
	"effective_from" text NOT NULL,
	"effective_to" text,
	"note" text
);
--> statement-breakpoint
CREATE TABLE "shops" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"seller_account_id" uuid NOT NULL,
	"tts_shop_id" text NOT NULL,
	"shop_name" text,
	"shop_cipher" text,
	"region" text DEFAULT 'US' NOT NULL,
	"category" text,
	"access_token_enc" text,
	"refresh_token_enc" text,
	"token_expires_at" timestamp with time zone,
	"status" text DEFAULT 'disconnected' NOT NULL,
	"last_synced_at" timestamp with time zone,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "statement_transactions" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"statement_id" uuid,
	"shop_id" uuid NOT NULL,
	"tts_order_id" text NOT NULL,
	"sku_id" text,
	"type" text DEFAULT 'order' NOT NULL,
	"currency" text DEFAULT 'USD' NOT NULL,
	"gross_sales" numeric(14, 4),
	"net_sales" numeric(14, 4),
	"customer_payment" numeric(14, 4),
	"sales_tax" numeric(14, 4),
	"referral_fee" numeric(14, 4),
	"transaction_fee" numeric(14, 4),
	"refund_admin_fee" numeric(14, 4),
	"affiliate_commission" numeric(14, 4),
	"shipping_actual" numeric(14, 4),
	"fbt_fees" numeric(14, 4),
	"adjustment_amount" numeric(14, 4),
	"adjustment_id" text,
	"settlement_amount" numeric(14, 4),
	"order_created_date" text,
	"raw" jsonb
);
--> statement-breakpoint
CREATE TABLE "statements" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"shop_id" uuid NOT NULL,
	"tts_statement_id" text NOT NULL,
	"statement_time" timestamp with time zone,
	"currency" text DEFAULT 'USD' NOT NULL,
	"settlement_amount" numeric(14, 4),
	"revenue_amount" numeric(14, 4),
	"fee_amount" numeric(14, 4),
	"shipping_cost_amount" numeric(14, 4),
	"adjustment_amount" numeric(14, 4),
	"payment_id" text,
	"source" text DEFAULT 'upload' NOT NULL,
	"raw" jsonb,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "subscriptions" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"seller_account_id" uuid NOT NULL,
	"stripe_subscription_id" text,
	"stripe_price_id" text,
	"plan" text NOT NULL,
	"status" text NOT NULL,
	"current_period_end" timestamp with time zone,
	"cancel_at_period_end" boolean DEFAULT false NOT NULL,
	CONSTRAINT "subscriptions_stripe_subscription_id_unique" UNIQUE("stripe_subscription_id")
);
--> statement-breakpoint
CREATE TABLE "uploads" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"seller_account_id" uuid,
	"shop_id" uuid,
	"filename" text,
	"parsed_rows" integer DEFAULT 0 NOT NULL,
	"skipped_rows" integer DEFAULT 0 NOT NULL,
	"unknown_headers" jsonb,
	"status" text DEFAULT 'parsed' NOT NULL,
	"email" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "discrepancies" ADD CONSTRAINT "discrepancies_run_id_reconciliation_runs_id_fk" FOREIGN KEY ("run_id") REFERENCES "public"."reconciliation_runs"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "discrepancies" ADD CONSTRAINT "discrepancies_shop_id_shops_id_fk" FOREIGN KEY ("shop_id") REFERENCES "public"."shops"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "reconciliation_runs" ADD CONSTRAINT "reconciliation_runs_shop_id_shops_id_fk" FOREIGN KEY ("shop_id") REFERENCES "public"."shops"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "reconciliation_runs" ADD CONSTRAINT "reconciliation_runs_upload_id_uploads_id_fk" FOREIGN KEY ("upload_id") REFERENCES "public"."uploads"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "shop_fee_overrides" ADD CONSTRAINT "shop_fee_overrides_shop_id_shops_id_fk" FOREIGN KEY ("shop_id") REFERENCES "public"."shops"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "shops" ADD CONSTRAINT "shops_seller_account_id_seller_accounts_id_fk" FOREIGN KEY ("seller_account_id") REFERENCES "public"."seller_accounts"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "statement_transactions" ADD CONSTRAINT "statement_transactions_statement_id_statements_id_fk" FOREIGN KEY ("statement_id") REFERENCES "public"."statements"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "statement_transactions" ADD CONSTRAINT "statement_transactions_shop_id_shops_id_fk" FOREIGN KEY ("shop_id") REFERENCES "public"."shops"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "statements" ADD CONSTRAINT "statements_shop_id_shops_id_fk" FOREIGN KEY ("shop_id") REFERENCES "public"."shops"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "subscriptions" ADD CONSTRAINT "subscriptions_seller_account_id_seller_accounts_id_fk" FOREIGN KEY ("seller_account_id") REFERENCES "public"."seller_accounts"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "uploads" ADD CONSTRAINT "uploads_seller_account_id_seller_accounts_id_fk" FOREIGN KEY ("seller_account_id") REFERENCES "public"."seller_accounts"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "uploads" ADD CONSTRAINT "uploads_shop_id_shops_id_fk" FOREIGN KEY ("shop_id") REFERENCES "public"."shops"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "discrepancies_run_idx" ON "discrepancies" USING btree ("run_id");--> statement-breakpoint
CREATE INDEX "discrepancies_status_idx" ON "discrepancies" USING btree ("status");--> statement-breakpoint
CREATE INDEX "shops_account_idx" ON "shops" USING btree ("seller_account_id");--> statement-breakpoint
CREATE UNIQUE INDEX "shops_account_tts_uidx" ON "shops" USING btree ("seller_account_id","tts_shop_id");--> statement-breakpoint
CREATE INDEX "stmt_tx_shop_idx" ON "statement_transactions" USING btree ("shop_id");--> statement-breakpoint
CREATE UNIQUE INDEX "stmt_tx_uidx" ON "statement_transactions" USING btree ("shop_id","tts_order_id","sku_id","type");--> statement-breakpoint
CREATE INDEX "statements_shop_idx" ON "statements" USING btree ("shop_id");--> statement-breakpoint
CREATE UNIQUE INDEX "statements_shop_tts_uidx" ON "statements" USING btree ("shop_id","tts_statement_id");