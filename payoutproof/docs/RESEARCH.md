# Market Research — why PayoutProof

This is the condensed, fact-checked output of a deep-research process: five
parallel research tracks (demand, niche saturation, solo-founder case studies,
zero-budget distribution, pricing/churn benchmarks) plus two adversarial
verification passes (a 10-claim fact-check and a competitor kill-test of the
top three ideas).

## Founder constraints

Solo engineer, near-zero marketing budget, B2B/SMB, global English market,
$20–200/mo subscription, target $5–20k MRR within 12 months, low churn, weak or
fragmented competition.

## What the research ruled out

- **Generic AI wrappers** — the #1 startup-shutdown category in 2025 (~16% of
  shutdowns); AI-native tools under $50/mo retain at ~23% gross revenue
  retention (ChartMogul "AI Churn Wave" report).
- **Horizontal tools** (task trackers, CRM, AI writers) — hundreds of
  near-zero-review clones.
- **Shopify ops niches** — Shopify absorbed B2B/wholesale into the platform for
  free (April 2026), the "Matrixify alternative" slot is already taken (Altera),
  and regulation-triggered niches get swarmed in under 12 months. **Killed.**
- **Vertical compliance logs** (daycare, food labels, cleaning) — every vertical
  examined already had both a funded incumbent and a budget-tier indie, and none
  had an app-store distribution channel. **Near-killed.**

## What survived

The strongest pattern for a zero-budget solo founder: **borrowed distribution**
(platform app stores + niche communities) × **system-of-record stickiness** ×
**a painful, quantifiable money problem** × **B2B pricing ($50+/mo)**.

The original idea — e-commerce bookkeeping sync for "underserved" marketplaces
(TikTok Shop / Etsy / Walmart) — was **killed by adversarial check**: Link My
Books, Synder, A2X, and ConnectBooks already cover those marketplaces directly.

But rotating the wedge 90° survived: those incumbents do **journal-entry sync
for accountants**; none of them **audit the payout for the seller**. A2X doesn't
even have a native TikTok Shop integration (verified). That gap is PayoutProof.

## Demand evidence

- ~216k active US TikTok Shop sellers; US GMV ~$13–16B in 2025, +87–108% YoY.
- r/TikTokShop and seller Discords carry recurring, specific complaints about
  unexplained payout shortfalls, shipping deductions not shown in payout
  reports, and held reserves.
- Regulatory overhang resolved: the US divestiture/JV deal closed January 2026.

## Distribution (zero budget)

1. **Free audit micro-tool** (engineering-as-marketing) → the lead magnet; needs
   no API approval because it parses the seller's own export.
2. **r/TikTokShop + own TikTok content** — sellers are creators, so "I audited a
   payout, here's what I found" demos are native; Reddit is also the most-cited
   source in LLM answers (GEO upside).
3. **TikTok Shop App Store** (exists, gives a listing) once the app is approved.
4. SEO/GEO pages on high-intent queries ("why is my TikTok Shop payout less than
   expected", "TikTok Shop referral fee calculator").

Declining channels deliberately avoided as primary: classic informational SEO
(AI-overview CTR collapse), Product Hunt (only ~10% of launches feature),
lifetime-deal platforms.

## Pricing & churn

ChartMogul/Optifai/ChartMogul data: price is a retention filter — sub-$50 AI
tools churn catastrophically; $50–250/mo sold to a business owner retains near
the B2B median. Financial/system-of-record workflows are sticky. Hence
$29–149/mo tiers and annual-billing nudges.

## Honest caveats (from the fact-check pass)

- "Guaranteed profit" is not a thing. Median time to $10k MRR is **9–18 months**;
  the six-week success stories are the far tail.
- Some widely-circulated stats ("43% of SMB churn in 90 days", "35–60% vertical
  retention edge", "$4.2k median micro-SaaS MRR") trace only to content farms —
  used directionally here, never as load-bearing figures.
- Shopify app count is ~17.5–18k (not the often-quoted 12k) — competition there
  is denser and faster-growing than headlines suggest, reinforcing the decision
  to avoid it.

## The bet

Build the payout-audit tool nobody else builds, distribute it free through the
communities where the pain is voiced, convert to a $29–149/mo subscription that
audits every settlement automatically, and keep burn near zero so the codebase
can pivot to Temu/Shein/Walmart payout audit if TikTok risk ever returns.
