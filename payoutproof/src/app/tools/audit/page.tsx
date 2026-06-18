import { AuditTool } from "./audit-tool";

export const metadata = {
  title: "Free TikTok Shop Payout Audit — PayoutProof",
  description:
    "Upload your TikTok Shop settlement export and instantly find overcharged fees, missing refund credits, and unpaid orders. Free, no login.",
};

export default function AuditToolPage() {
  return (
    <main className="container">
      <section className="hero" style={{ paddingBottom: 24 }}>
        <h1>Free TikTok Shop payout audit</h1>
        <p className="lead">
          Export your statements from Seller Center → Finance → Statements → Export, then
          drop the file below. Nothing is stored — the audit runs in your session.
        </p>
      </section>
      <AuditTool />
      <footer>
        Tip: the order-level export (with one row per order/SKU) gives the most accurate
        audit. Summary-only exports limit some checks.
      </footer>
    </main>
  );
}
