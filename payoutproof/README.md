# PayoutProof

**Find the money TikTok Shop owes you.**

PayoutProof is a payout-audit SaaS for TikTok Shop sellers. It ingests
settlement data (via the TikTok Shop Finance API or a Seller Center export),
recomputes what the seller *should* have been paid — referral fees, shipping
deductions, affiliate commissions, refund clawbacks, withholds — and flags
every discrepancy with a CSV evidence pack the seller can take to TikTok
support.

It is **not** another bookkeeping sync (Link My Books, A2X, Synder already own
that). Those tools generate journal entries for accountants. PayoutProof audits
the payout itself for the seller. That is the wedge.

---

## Why this exists

Full market research and the strategic rationale live in
[`docs/RESEARCH.md`](docs/RESEARCH.md). The short version: incumbents post the
numbers TikTok reports; nobody checks whether those numbers are *correct*.
TikTok Shop has ~216k active US shops and growing GMV, sellers routinely
complain about unexplained payout shortfalls, and the platform's regulatory
overhang resolved in early 2026.

## Architecture

Boring and cheap on purpose (target < $50/mo infra). One Next.js app serves the
marketing site, the free audit tool, and the authenticated dashboard; one
always-on worker runs the sync queue. Postgres is the only datastore (pg-boss
uses it as the queue — no Redis).

```
Next.js 15 (App Router, TS) ── web + free tool + API routes
        │
        ├─ /api/audit          parse XLSX → reconcile → report   (no auth, lead magnet)
        ├─ /api/checkout        Stripe Checkout (14-day trial)
        ├─ /api/stripe/webhook  subscription lifecycle
        └─ /api/tiktok/*        OAuth connect + callback
Worker (pg-boss) ── sync-shop: pull Finance API → upsert → reconcile, every 8h
Postgres (Neon or local) ── multi-tenant, money as numeric(14,4)
```

### The reconciliation engine (`src/lib/engine/reconcile.ts`)

A **pure, deterministic, versioned** function — the crown jewel. Same input +
same fee schedule ⇒ same discrepancies. No I/O. Checks, in order of customer
value:

1. **Internal consistency** — every line must satisfy
   `revenue − fees − shipping + adjustments = settlement`.
2. **Referral fee** — expected `rate(region, category, date) × base` vs actual.
3. **Refund clawback** — refunds must return 80% of the referral fee (20% admin
   retention).
4. **Unsettled aging** — delivered-but-unpaid orders and reserves held too long.
5. **Duplicate adjustments** — the same adjustment id charged twice.

Fee rates are **data, not code** (`fee_schedules` table + `shop_fee_overrides`
for promos/negotiated rates), each row carrying an effective-date window, so
audits stay reproducible after TikTok changes rates.

### Source-agnostic ingestion

The XLSX parser (`settlement-xlsx-parser.ts`) and the Finance API mapper
(`map-finance.ts`) both emit the same normalized `SettlementTransaction`. The
engine cannot tell which source produced a row. This is why the free
upload-tool ships before TikTok API approval (which takes 3+ weeks) and why API
risk is survivable — uploads are a permanent first-class path.

## Local development

```bash
cp .env.example .env          # fill in secrets; generate ENCRYPTION_KEY with: openssl rand -base64 32
npm install
docker compose up -d db       # or point DATABASE_URL at Neon
npm run db:migrate            # apply drizzle/*.sql
npm run db:seed               # seed fee schedules
npm run dev                   # web on :3000
npm run worker                # in another shell, for API sync
```

### Tests

```bash
npm test          # 36 unit tests: engine, parser, money, signing, crypto
npm run typecheck
npm run build
```

The engine and parser are covered by fixtures in `tests/`. Add real
(anonymized) Seller Center exports under `tests/` and assert the invariants
before trusting a new column layout.

## Deployment (single VPS)

```bash
# On a $12/mo Hetzner/DO box with Docker:
cp .env.example .env          # production secrets; set DOMAIN for Caddy
docker compose up -d          # db + web + worker + Caddy (auto-TLS)
docker compose run --rm web npm run db:migrate
docker compose run --rm web npm run db:seed
```

Caddy terminates TLS and reverse-proxies to the web container. The worker runs
the same image with `npm run worker`.

## TikTok Shop setup

1. Register as an app developer in the TikTok Shop Partner Center (US:
   `partner.us.tiktokshop.com`). Create an app requesting **read-only Finance +
   Orders** scopes.
2. Submit for compliance review (**3+ weeks** for US/UK — start day one).
3. Put the app key/secret in `.env`. Set the OAuth redirect to
   `${APP_URL}/api/tiktok/callback`.
4. Test against a Development Shop before approval.

Until approval lands, the product runs entirely on the XLSX-upload path.

## Stripe setup

Create four recurring prices and put their ids in `.env`
(`STRIPE_PRICE_STARTER/GROWTH/PRO/AGENCY`). Point a webhook at
`${APP_URL}/api/stripe/webhook` for `checkout.session.completed` and
`customer.subscription.*` events.

## Status

Production-ready core: reconciliation engine, ingestion (upload + API),
multi-tenant schema + migrations, Stripe billing, TikTok OAuth + sync worker,
free audit tool, deployment config, 36 passing tests, clean typecheck and
build.

Deliberately deferred (see [`docs/ROADMAP.md`](docs/ROADMAP.md)): session auth
wiring (Better Auth), QuickBooks/Xero OAuth export, affiliate-rate verification,
multi-user teams, the TikTok Shop App Store listing.

## Legal

PayoutProof is independent and not affiliated with TikTok. Findings are
estimates to investigate, not guarantees of owed amounts.
