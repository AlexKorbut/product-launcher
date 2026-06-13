import Link from "next/link";

export const metadata = { title: "Dashboard — PayoutProof" };

/**
 * Authenticated dashboard shell. Auth wiring (Better Auth) and live data are
 * layered in once a session exists; this renders the connected-shop and
 * recovery-tracking surfaces the app is organized around.
 */
export default async function AppDashboard({
  searchParams,
}: {
  searchParams: Promise<{ connect?: string; checkout?: string }>;
}) {
  const params = await searchParams;
  const connected = params.connect === "success";
  return (
    <main className="container">
      <section className="hero" style={{ paddingBottom: 16 }}>
        <h1>Your payout audits</h1>
      </section>

      {connected && (
        <div className="panel" style={{ borderColor: "var(--accent)" }}>
          Shop connected. Your next settlement will be audited automatically.
        </div>
      )}

      <div className="grid mt">
        <div className="panel">
          <h3>Recovered to date</h3>
          <div style={{ fontSize: "2rem", fontWeight: 800 }} className="owed">$0.00</div>
          <p className="muted">Mark findings as recovered to track what TikTok pays back.</p>
        </div>
        <div className="panel">
          <h3>Open findings</h3>
          <div style={{ fontSize: "2rem", fontWeight: 800 }}>—</div>
          <p className="muted">Connect a shop or upload a statement to begin.</p>
        </div>
      </div>

      <div className="panel mt">
        <h3>Connect your TikTok Shop</h3>
        <p className="muted">
          Authorize read-only access to your finance data. We never see your bank details
          and request the minimum scopes (Finance + Orders).
        </p>
        <a className="btn" href="/api/tiktok/connect">Connect TikTok Shop</a>
      </div>

      <div className="panel mt">
        <h3>Or upload a statement</h3>
        <p className="muted">No connection needed — audit a settlement export right now.</p>
        <Link className="btn secondary" href="/tools/audit">Upload settlement export</Link>
      </div>
    </main>
  );
}
