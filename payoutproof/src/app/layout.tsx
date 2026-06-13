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
      <body>{children}</body>
    </html>
  );
}
