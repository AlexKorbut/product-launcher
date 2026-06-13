# 12-Month Roadmap → $5–20k MRR

Blended ARPU ≈ $50 ⇒ $5k MRR ≈ 100 customers, $20k ≈ ~350–400 (incl. agency
tier). Against ~216k US shops that is 0.05–0.2% penetration.

## Month 0–1 — Validate while building

- 10–15 seller interviews from r/TikTokShop and seller Discords. Ask: "have you
  ever checked your statement math?" and "show me a payout you didn't
  understand."
- Landing page + waitlist.
- **Gate:** run 5 real seller exports through the engine by hand. If ≥3 of 5
  surface real discrepancies ≥ $10, the pitch writes itself. If not — **stop and
  pivot the engine to Temu/Shein/Walmart** before building further.
- Submit the TikTok Partner Center app for compliance review (3+ week clock runs
  in parallel).

## Month 2 — Launch the free tool

- Ship `/tools/audit` publicly. Post anonymized findings to r/TikTokShop; record
  short TikToks auditing payouts.
- Goal: 300 free audits, 500 emails.

## Month 3 — Paid launch

- Convert free users (in-product upsell: "automate this every payout + track
  recovery").
- Concierge audits for the first 20 customers, free, in exchange for
  testimonials and fixture data.
- Goal: 30 paying.

## Month 4–6 — API sync + App Store

- Flip on OAuth sync (the ingestion layer is already source-agnostic).
- Submit the TikTok Shop App Store listing.
- Ship the QuickBooks-friendly journal CSV export.
- Goal: 100 paying, ~$4–5k MRR.

## Month 7–12 — Compounding distribution

- App Store reviews flywheel; referral program for TikTok-seller influencers and
  agencies (agency tier, multi-shop).
- Xero/QBO OAuth export only if customers pull for it.
- UK expansion (region column already everywhere).

## Key metrics

- **% of audits surfacing ≥ $10 in discrepancies** — the magic number; the whole
  funnel depends on it. Instrument first.
- audit → trial → paid conversion.
- **$ flagged vs $ marked recovered** — the retention driver and the moat.
- Churn; sync failure rate; parser unknown-column rate.

## Top risks & mitigations

1. **Platform API risk** → XLSX upload is permanent first-class; `raw jsonb`
   keeps source data for cheap re-normalization.
2. **Incumbent copies the feature** → they sell to accountants; we sell "found
   money" to sellers; moat = recovery workflow (statuses, evidence packs,
   recovered-$ tracking). Assume a ~12-month window.
3. **TikTok US regulatory residual risk** → region column everywhere; engine
   generalizes to other marketplaces; near-zero burn survives a pause.
4. **False positives** (worst failure: telling a seller they're owed money when
   they aren't) → tolerances + calibration mode + "explained" status + manual
   review of the first 20 customers' reports.
5. **Single-channel concentration** → three channels by month 6 (Reddit, own
   TikTok, App Store) plus high-intent SEO/GEO pages.
