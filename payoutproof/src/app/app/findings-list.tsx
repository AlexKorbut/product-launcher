"use client";

import { useState } from "react";
import type { FindingRow } from "../../lib/services/account-queries";

const CHECK_LABELS: Record<string, string> = {
  internal_consistency: "Unbalanced statement",
  referral_fee: "Referral fee overcharge",
  refund_clawback: "Missing refund credit",
  unsettled_aging: "Unpaid / held order",
  duplicate_adjustment: "Duplicate adjustment",
};

const fmt = (cents: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100);

export function FindingsList({ initial }: { initial: FindingRow[] }) {
  const [rows, setRows] = useState(initial);
  const [busy, setBusy] = useState<string | null>(null);

  async function setStatus(id: string, status: string) {
    setBusy(id);
    try {
      const res = await fetch(`/api/discrepancies/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (res.ok) {
        // Remove from the open list once it leaves "open".
        setRows((prev) => prev.filter((r) => r.id !== id));
      }
    } finally {
      setBusy(null);
    }
  }

  if (rows.length === 0) {
    return <p className="muted">No open findings. Connect a shop or upload a statement to run an audit.</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Issue</th>
          <th>Order</th>
          <th style={{ textAlign: "right" }}>Owed</th>
          <th style={{ textAlign: "right" }}>Actions</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.id}>
            <td>
              <span className={`badge ${r.severity}`}>{r.severity}</span>{" "}
              {CHECK_LABELS[r.checkId] ?? r.checkId}
            </td>
            <td className="muted">{r.orderId ?? "—"}</td>
            <td style={{ textAlign: "right" }} className="owed">{fmt(r.deltaCents)}</td>
            <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
              <button
                className="btn secondary"
                disabled={busy === r.id}
                onClick={() => setStatus(r.id, "recovered")}
                style={{ padding: "6px 10px", fontSize: "0.8rem" }}
              >
                Recovered
              </button>{" "}
              <button
                className="btn secondary"
                disabled={busy === r.id}
                onClick={() => setStatus(r.id, "dismissed")}
                style={{ padding: "6px 10px", fontSize: "0.8rem" }}
              >
                Dismiss
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
