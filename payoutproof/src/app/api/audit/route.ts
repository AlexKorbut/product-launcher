import { NextRequest, NextResponse } from "next/server";
import { parseSettlementWorkbook } from "../../../lib/ingest/settlement-xlsx-parser";
import { reconcile } from "../../../lib/engine/reconcile";
import { buildAuditReport } from "../../../lib/report";
import type { Region } from "../../../lib/engine/types";

export const runtime = "nodejs";
export const maxDuration = 30;

const MAX_BYTES = 15 * 1024 * 1024; // 15 MB

/**
 * Free-tool audit endpoint. Accepts a settlement export (multipart file),
 * parses → reconciles → returns a report. No persistence required for the
 * anonymous path; the email gate (handled client-side + /api/lead) is what
 * captures the contact. This is the zero-friction lead magnet.
 */
export async function POST(req: NextRequest) {
  try {
    const form = await req.formData();
    const file = form.get("file");
    const region = (String(form.get("region") ?? "US").toUpperCase() as Region) || "US";
    const category = form.get("category") ? String(form.get("category")) : undefined;

    if (!(file instanceof File)) {
      return NextResponse.json({ error: "No file uploaded." }, { status: 400 });
    }
    if (file.size > MAX_BYTES) {
      return NextResponse.json({ error: "File too large (max 15 MB)." }, { status: 413 });
    }

    const buf = new Uint8Array(await file.arrayBuffer());
    const parsed = parseSettlementWorkbook(buf, { defaultCurrency: region === "GB" ? "GBP" : "USD" });

    if (parsed.transactions.length === 0) {
      return NextResponse.json(
        {
          error:
            "We couldn't find any transaction rows. Make sure you uploaded the order-level settlement export from Seller Center → Finance → Statements → Export.",
          unknownHeaders: parsed.unknownHeaders,
        },
        { status: 422 },
      );
    }

    const result = reconcile({
      region,
      shopCategory: category,
      transactions: parsed.transactions,
    });
    const report = buildAuditReport(result, parsed.currency);

    return NextResponse.json({
      report,
      parse: {
        rows: parsed.transactions.length,
        skipped: parsed.skippedRows,
        unknownHeaders: parsed.unknownHeaders,
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unexpected error";
    return NextResponse.json({ error: `Could not process file: ${message}` }, { status: 500 });
  }
}
