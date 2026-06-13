import { signRequest } from "./sign";

export interface TikTokClientConfig {
  appKey: string;
  appSecret: string;
  apiBase: string;
  authBase: string;
}

export interface ShopAuth {
  accessToken: string;
  shopCipher: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  access_token_expire_in: number;
  refresh_token_expire_in: number;
  open_id?: string;
  seller_name?: string;
}

const FINANCE_VERSION = "202501";
const FINANCE_LEGACY_VERSION = "202309";

interface FetchOptions {
  method?: "GET" | "POST";
  query?: Record<string, string | number | undefined>;
  body?: unknown;
  auth?: ShopAuth;
  /** retry budget for 429 / 5xx */
  retries?: number;
}

export class TikTokShopClient {
  constructor(private readonly cfg: TikTokClientConfig) {}

  /** Exchange an authorization code for access + refresh tokens. */
  async exchangeCode(authCode: string): Promise<TokenResponse> {
    const url = new URL("/api/v2/token/get", this.cfg.authBase);
    url.searchParams.set("app_key", this.cfg.appKey);
    url.searchParams.set("app_secret", this.cfg.appSecret);
    url.searchParams.set("auth_code", authCode);
    url.searchParams.set("grant_type", "authorized_code");
    const res = await fetch(url, { method: "GET" });
    return unwrap<TokenResponse>(await res.json());
  }

  async refreshToken(refreshToken: string): Promise<TokenResponse> {
    const url = new URL("/api/v2/token/refresh", this.cfg.authBase);
    url.searchParams.set("app_key", this.cfg.appKey);
    url.searchParams.set("app_secret", this.cfg.appSecret);
    url.searchParams.set("refresh_token", refreshToken);
    url.searchParams.set("grant_type", "refresh_token");
    const res = await fetch(url, { method: "GET" });
    return unwrap<TokenResponse>(await res.json());
  }

  /** List shops authorized for this access token (yields shop_cipher). */
  async getAuthorizedShops(accessToken: string): Promise<
    { id: string; name: string; region: string; cipher: string }[]
  > {
    const data = await this.call<{ shops: { id: string; name: string; region: string; cipher: string }[] }>(
      "/authorization/202309/shops",
      { auth: { accessToken, shopCipher: "" } },
    );
    return data.shops ?? [];
  }

  /** Finance API — settlement statements since a time window. */
  async getStatements(
    auth: ShopAuth,
    params: { statementTimeGe?: number; statementTimeLt?: number; pageToken?: string; pageSize?: number },
  ): Promise<{ statements: RawStatement[]; nextPageToken?: string }> {
    const data = await this.call<{ statements: RawStatement[]; next_page_token?: string }>(
      `/finance/${FINANCE_VERSION}/statements`,
      {
        auth,
        query: {
          statement_time_ge: params.statementTimeGe,
          statement_time_lt: params.statementTimeLt,
          page_size: params.pageSize ?? 50,
          page_token: params.pageToken,
          sort_field: "statement_time",
        },
      },
    );
    return { statements: data.statements ?? [], nextPageToken: data.next_page_token };
  }

  /** Finance API — per-order/SKU transactions under a statement. */
  async getStatementTransactions(
    auth: ShopAuth,
    statementId: string,
    pageToken?: string,
  ): Promise<{ transactions: RawStatementTransaction[]; nextPageToken?: string }> {
    const data = await this.call<{
      statement_transactions: RawStatementTransaction[];
      next_page_token?: string;
    }>(`/finance/${FINANCE_VERSION}/statements/${statementId}/statement_transactions`, {
      auth,
      query: { page_size: 100, page_token: pageToken, sort_field: "order_create_time" },
    });
    return {
      transactions: data.statement_transactions ?? [],
      nextPageToken: data.next_page_token,
    };
  }

  async getPayments(
    auth: ShopAuth,
    params: { createTimeGe?: number; pageToken?: string },
  ): Promise<{ payments: RawPayment[]; nextPageToken?: string }> {
    const data = await this.call<{ payments: RawPayment[]; next_page_token?: string }>(
      `/finance/${FINANCE_LEGACY_VERSION}/payments`,
      { auth, query: { create_time_ge: params.createTimeGe, page_size: 50, page_token: params.pageToken } },
    );
    return { payments: data.payments ?? [], nextPageToken: data.next_page_token };
  }

  /** Signed request core with 429/5xx backoff. */
  private async call<T>(path: string, opts: FetchOptions = {}): Promise<T> {
    const retries = opts.retries ?? 4;
    const timestamp = Math.floor(Date.now() / 1000);
    const bodyStr = opts.body ? JSON.stringify(opts.body) : undefined;

    const query: Record<string, string | number | undefined> = {
      app_key: this.cfg.appKey,
      timestamp,
      ...opts.query,
    };
    if (opts.auth?.shopCipher) query.shop_cipher = opts.auth.shopCipher;

    const sign = signRequest({ appSecret: this.cfg.appSecret, path, query, body: bodyStr });

    const url = new URL(path, this.cfg.apiBase);
    for (const [k, v] of Object.entries({ ...query, sign })) {
      if (v !== undefined && v !== "") url.searchParams.set(k, String(v));
    }

    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (opts.auth?.accessToken) headers["x-tts-access-token"] = opts.auth.accessToken;

    let lastError: unknown;
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const res = await fetch(url, {
          method: opts.method ?? "GET",
          headers,
          body: bodyStr,
        });
        if (res.status === 429 || res.status >= 500) {
          throw new RetryableError(`TikTok API ${res.status}`);
        }
        return unwrap<T>(await res.json());
      } catch (err) {
        lastError = err;
        if (!(err instanceof RetryableError) || attempt === retries) break;
        await sleep(2 ** attempt * 1000 + Math.random() * 250);
      }
    }
    throw lastError;
  }
}

class RetryableError extends Error {}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

/** TikTok wraps every response as { code, message, data, request_id }. */
function unwrap<T>(payload: unknown): T {
  const p = payload as { code?: number; message?: string; data?: T };
  if (p && typeof p.code === "number" && p.code !== 0) {
    throw new Error(`TikTok API error ${p.code}: ${p.message ?? "unknown"}`);
  }
  return (p?.data ?? (payload as T)) as T;
}

// ---- Raw response shapes (subset of fields we consume) ----

export interface RawStatement {
  id: string;
  statement_time?: string | number;
  currency?: string;
  settlement_amount?: string;
  revenue_amount?: string;
  fee_amount?: string;
  shipping_cost_amount?: string;
  adjustment_amount?: string;
  payment_id?: string;
}

export interface RawStatementTransaction {
  id?: string;
  order_id?: string;
  sku_id?: string;
  type?: string;
  order_create_time?: string | number;
  currency?: string;
  settlement_amount?: string;
  revenue_amount?: string;
  fee_tax_amount?: string;
  shipping_cost_amount?: string;
  adjustment_amount?: string;
  adjustment_id?: string;
  sku_transactions?: RawSkuTransaction[];
  // flattened fee fields (vary by version; consumed defensively)
  referral_fee_amount?: string;
  transaction_fee_amount?: string;
  refund_administration_fee_amount?: string;
  affiliate_commission_amount?: string;
  customer_payment_amount?: string;
  sales_tax_amount?: string;
}

export interface RawSkuTransaction {
  sku_id?: string;
  revenue_amount?: string;
  fee_and_tax_amount?: string;
  shipping_cost_amount?: string;
  settlement_amount?: string;
}

export interface RawPayment {
  id: string;
  create_time?: string | number;
  amount?: string;
  status?: string;
}
