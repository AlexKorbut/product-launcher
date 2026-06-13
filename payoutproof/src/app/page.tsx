import Link from "next/link";

export default function HomePage() {
  return (
    <main className="container">
      <section className="hero">
        <h1>
          Find the money <span className="accent">TikTok Shop owes you</span>
        </h1>
        <p className="lead">
          TikTok Shop deducts referral fees, shipping costs, affiliate commissions and
          adjustments on every payout — and gets them wrong more often than you think.
          PayoutProof recomputes every line of your settlement and shows you exactly what
          you were underpaid.
        </p>
        <Link href="/tools/audit" className="btn">
          Run a free payout audit →
        </Link>
        <p className="muted mt">No login. Upload your settlement export, get results in seconds.</p>
      </section>

      <section className="grid mt-lg">
        <div className="panel">
          <h3>Overcharged fees</h3>
          <p className="muted">
            We know the current US/UK referral-fee schedule and flag any order where TikTok
            charged more than the rate you should have paid.
          </p>
        </div>
        <div className="panel">
          <h3>Missing refund credits</h3>
          <p className="muted">
            Refunds are supposed to return 80% of the referral fee. We catch the ones that
            didn't.
          </p>
        </div>
        <div className="panel">
          <h3>Unpaid &amp; held money</h3>
          <p className="muted">
            Delivered orders that never settled and reserves held past their window — the
            money TikTok is quietly sitting on.
          </p>
        </div>
        <div className="panel">
          <h3>Statements that don&apos;t balance</h3>
          <p className="muted">
            Every line must satisfy revenue − fees − shipping + adjustments = payout. We
            check the math TikTok hopes you never will.
          </p>
        </div>
      </section>

      <section className="panel mt-lg center">
        <h2>Connect once, audited every payout</h2>
        <p className="muted">
          Start free with a one-off upload. Upgrade to connect your shop and have every
          settlement audited automatically, with a recovery worksheet you can take to
          TikTok seller support.
        </p>
        <div className="mt">
          <Link href="/tools/audit" className="btn">Free audit</Link>{" "}
          <Link href="/pricing" className="btn secondary">See pricing</Link>
        </div>
      </section>

      <footer>
        <p>
          PayoutProof is an independent tool and is not affiliated with or endorsed by
          TikTok. Findings are estimates to investigate, not guarantees of owed amounts.
        </p>
      </footer>
    </main>
  );
}
