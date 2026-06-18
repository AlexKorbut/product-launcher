import { NextResponse } from "next/server";
import { getSession } from "../../../../lib/auth/session";
import { getDiscrepanciesForExport } from "../../../../lib/services/account-queries";

export const runtime = "nodejs";

/**
 * Evidence-pack CSV: every discrepancy across the account's shops, with
 * expected vs actual and the amount owed. This is what the seller attaches to
 * a TikTok seller-support ticket.
 */
export async function GET() {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const rows = await getDiscrepanciesForExport(session.accountId);
  const header = [
    "check",
    "order_id",
    "sku_id",
    "fee_type",
    "expected",
    "actual",
    "amount_owed",
    "severity",
    "status",
  ];
  const body = rows.map((r) =>
    [
      r.checkId,
      r.orderId ?? "",
      r.skuId ?? "",
      r.feeType ?? "",
      r.expected ?? "",
      r.actual ?? "",
      r.delta ?? "",
      r.severity,
      r.status,
    ]
      .map(csvEscape)
      .join(","),
  );
  const csv = [header.join(","), ...body].join("\n");

  return new NextResponse(csv, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="payoutproof-evidence-${new Date().toISOString().slice(0, 10)}.csv"`,
    },
  });
}

function csvEscape(value: string): string {
  return /[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
}
