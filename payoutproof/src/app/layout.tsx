import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PayoutProof — Find the money TikTok Shop owes you",
  description:
    "Audit your TikTok Shop payouts. We recompute every fee, shipping deduction, refund and adjustment to find money TikTok owes you. Free instant audit from your settlement export.",
  openGraph: {
    title: "PayoutProof — Find the money TikTok Shop owes you",
    description:
      "Upload your TikTok Shop settlement export and instantly see overcharged fees, missing refunds and unpaid orders.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav style={{ borderBottom: "1px solid var(--border)" }}>
          <div
            className="container"
            style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 20px" }}
          >
            <a href="/" style={{ fontWeight: 800, color: "var(--text)" }}>
              Payout<span className="accent">Proof</span>
            </a>
            <div style={{ display: "flex", gap: 18, alignItems: "center" }}>
              <a href="/tools/audit">Free audit</a>
              <a href="/pricing">Pricing</a>
              <a href="/app" className="btn secondary" style={{ padding: "8px 14px" }}>
                Sign in
              </a>
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
