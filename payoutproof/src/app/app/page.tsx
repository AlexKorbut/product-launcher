import Link from "next/link";
import { redirect } from "next/navigation";
import { getSession } from "../../lib/auth/session";
import { getDashboardData } from "../../lib/services/account-queries";
import { FindingsList } from "./findings-list";

export const metadata = { title: "Dashboard — PayoutProof" };
export const dynamic = "force-dynamic";

const fmt = (cents: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100);

export default async function AppDashboard({
  searchParams,
}: {
  searchParams: Promise<{ connect?: string; checkout?: string }>;
}) {
  const session = await getSession();
  if (!session) redirect("/login?next=/app");

  const params = await searchParams;
  const data = await getDashboardData(session.accountId);
  if (!data) redirect("/login");

  const hasShop = data.shops.length > 0;

  return (
    <main className="container">
      <section className="hero" style={{ paddingBottom: 8, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ margin: 0 }}>Your payout audits</h1>
        <form action="/api/auth/logout" method="POST">
          <button className="btn secondary" type="submit" style={{ padding: "8px 14px" }}>Sign out</button>
        </form>
      </section>
      <p className="muted">{data.email} · {data.plan} plan ({data.planStatus})</p>

      {params.connect === "success" && (
        <div className="panel" style={{ borderColor: "var(--accent)" }}>
          Shop connected. Your next settlement will be audited automatically.
        </div>
      )}
      {params.checkout === "success" && (
        <div className="panel" style={{ borderColor: "var(--accent)" }}>
          Subscription active — welcome aboard. Connect your shop to start auto-audits.
        </div>
      )}

      <div className="grid mt">
        <div className="panel">
          <h3>Money TikTok may owe you</h3>
          <div style={{ fontSize: "2rem", fontWeight: 800 }} className="owed">{fmt(data.openOwedCents)}</div>
          <p className="muted">{data.openCount} open findings</p>
        </div>
        <div className="panel">
          <h3>Recovered to date</h3>
          <div style={{ fontSize: "2rem", fontWeight: 800 }} className="owed">{fmt(data.recoveredCents)}</div>
          <p className="muted">Marked recovered after TikTok paid back.</p>
        </div>
      </div>

      <div className="panel mt">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ margin: 0 }}>Open findings</h3>
          {hasShop && (
            <a className="btn secondary" href="/api/exports/journal" style={{ padding: "8px 14px" }}>
              Export evidence (CSV)
            </a>
          )}
        </div>
        <div className="mt">
          <FindingsList initial={data.topFindings} />
        </div>
      </div>

      <div className="grid mt">
        <div className="panel">
          <h3>Connect your TikTok Shop</h3>
          <p className="muted">
            Authorize read-only Finance + Orders access. Every settlement gets audited
            automatically.
          </p>
          {hasShop ? (
            <ul className="muted">
              {data.shops.map((s) => (
                <li key={s.id}>
                  {s.name ?? s.id} · {s.region} · {s.status}
                  {s.lastSyncedAt ? ` · synced ${s.lastSyncedAt.toISOString().slice(0, 10)}` : ""}
                </li>
              ))}
            </ul>
          ) : (
            <a className="btn" href={`/api/tiktok/connect?account=${session.accountId}`}>Connect TikTok Shop</a>
          )}
        </div>
        <div className="panel">
          <h3>Upload a statement</h3>
          <p className="muted">No connection needed — audit a settlement export right now.</p>
          <Link className="btn secondary" href="/tools/audit">Upload settlement export</Link>
        </div>
      </div>
    </main>
  );
}
