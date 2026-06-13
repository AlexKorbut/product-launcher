import Link from "next/link";

export const metadata = { title: "Pricing — PayoutProof" };

const tiers = [
  { plan: "starter", name: "Starter", price: "$29/mo", cap: "Up to 500 orders/mo", best: false },
  { plan: "growth", name: "Growth", price: "$49/mo", cap: "Up to 2,500 orders/mo", best: true },
  { plan: "pro", name: "Pro", price: "$79/mo", cap: "Up to 10,000 orders/mo", best: false },
  { plan: "agency", name: "Agency", price: "$149/mo", cap: "Unlimited orders · multi-shop", best: false },
];

export default function PricingPage() {
  return (
    <main className="container">
      <section className="hero" style={{ paddingBottom: 24 }}>
        <h1>Audit every payout, automatically</h1>
        <p className="lead">
          Every plan includes a 14-day free trial, automated settlement audits, recovery
          tracking, and CSV evidence packs. Cancel anytime.
        </p>
      </section>

      <div className="grid">
        {tiers.map((t) => (
          <div key={t.plan} className="panel" style={t.best ? { borderColor: "var(--accent)" } : undefined}>
            {t.best && <span className="badge" style={{ color: "var(--accent)", borderColor: "var(--accent)" }}>Most popular</span>}
            <h3 style={{ marginBottom: 4 }}>{t.name}</h3>
            <div style={{ fontSize: "1.8rem", fontWeight: 800 }}>{t.price}</div>
            <p className="muted">{t.cap}</p>
            <form action="/api/checkout" method="POST">
              <input type="hidden" name="plan" value={t.plan} />
              <button className="btn" type="submit" style={{ width: "100%" }}>Start free trial</button>
            </form>
          </div>
        ))}
      </div>

      <p className="muted center mt-lg">
        Not ready? <Link href="/tools/audit">Run a free one-off audit</Link> first.
      </p>
    </main>
  );
}
