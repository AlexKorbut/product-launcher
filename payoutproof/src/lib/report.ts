import { formatCents, type Cents } from "./money";
import type { CheckId, Discrepancy, ReconciliationResult } from "./engine/types";

const CHECK_LABELS: Record<CheckId, string> = {
  internal_consistency: "Statements that don't balance",
  referral_fee: "Referral fee overcharges",
  refund_clawback: "Refunds missing returned fees",
  unsettled_aging: "Delivered orders never paid out",
  duplicate_adjustment: "Duplicate adjustment charges",
};

export interface AuditReport {
  headline: string;
  totalOwedCents: Cents;
  totalOwedFormatted: string;
  transactionsChecked: number;
  discrepancyCount: number;
  /** the most valuable findings, capped for display */
  topFindings: ReportFinding[];
  sections: ReportSection[];
  engineVersion: string;
}

export interface ReportSection {
  checkId: CheckId;
  label: string;
  count: number;
  owedCents: Cents;
  owedFormatted: string;
}

export interface ReportFinding {
  checkId: CheckId;
  label: string;
  orderId?: string;
  deltaFormatted: string;
  deltaCents: Cents;
  severity: Discrepancy["severity"];
  message: string;
}

export function buildAuditReport(
  result: ReconciliationResult,
  currency = "USD",
  topN = 20,
): AuditReport {
  const sections: ReportSection[] = (
    Object.entries(result.summary) as [CheckId, { count: number; owedCents: Cents }][]
  )
    .filter(([, v]) => v.count > 0)
    .map(([checkId, v]) => ({
      checkId,
      label: CHECK_LABELS[checkId],
      count: v.count,
      owedCents: v.owedCents,
      owedFormatted: formatCents(v.owedCents, currency),
    }))
    .sort((a, b) => b.owedCents - a.owedCents);

  const topFindings: ReportFinding[] = result.discrepancies
    .filter((d) => d.delta > 0)
    .slice(0, topN)
    .map((d) => ({
      checkId: d.checkId,
      label: CHECK_LABELS[d.checkId],
      orderId: d.orderId,
      deltaCents: d.delta,
      deltaFormatted: formatCents(d.delta, currency),
      severity: d.severity,
      message: d.message,
    }));

  return {
    headline: buildHeadline(result.totalOwedCents, result.discrepancies.length, currency),
    totalOwedCents: result.totalOwedCents,
    totalOwedFormatted: formatCents(result.totalOwedCents, currency),
    transactionsChecked: result.transactionsChecked,
    discrepancyCount: result.discrepancies.filter((d) => d.delta > 0).length,
    topFindings,
    sections,
    engineVersion: result.engineVersion,
  };
}

function buildHeadline(
  owed: Cents,
  count: number,
  currency: string,
): string {
  if (count === 0 || owed <= 0) {
    return "No payout discrepancies found — your TikTok Shop statements balance.";
  }
  return `We found ${formatCents(owed, currency)} that TikTok Shop may owe you across ${count} line items.`;
}

/** Flat CSV of every positive-delta finding — the seller's evidence pack. */
export function discrepanciesToCsv(
  result: ReconciliationResult,
  currency = "USD",
): string {
  const header = [
    "check",
    "order_id",
    "sku_id",
    "fee_type",
    "expected",
    "actual",
    "amount_owed",
    "severity",
    "message",
  ];
  const rows = result.discrepancies.map((d) => [
    d.checkId,
    d.orderId ?? "",
    d.skuId ?? "",
    d.feeType ?? "",
    (d.expected / 100).toFixed(2),
    (d.actual / 100).toFixed(2),
    (d.delta / 100).toFixed(2),
    d.severity,
    csvEscape(d.message),
  ]);
  void currency;
  return [header, ...rows].map((r) => r.join(",")).join("\n");
}

function csvEscape(value: string): string {
  if (/[",\n]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}
