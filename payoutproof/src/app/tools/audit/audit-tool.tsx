"use client";

import { useCallback, useRef, useState } from "react";
import type { AuditReport } from "../../../lib/report";

type State =
  | { phase: "idle" }
  | { phase: "uploading" }
  | { phase: "done"; report: AuditReport; unknownHeaders: string[] }
  | { phase: "error"; message: string; unknownHeaders?: string[] };

export function AuditTool() {
  const [state, setState] = useState<State>({ phase: "idle" });
  const [region, setRegion] = useState("US");
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const upload = useCallback(
    async (file: File) => {
      setState({ phase: "uploading" });
      const form = new FormData();
      form.set("file", file);
      form.set("region", region);
      try {
        const res = await fetch("/api/audit", { method: "POST", body: form });
        const data = await res.json();
        if (!res.ok) {
          setState({ phase: "error", message: data.error ?? "Upload failed", unknownHeaders: data.unknownHeaders });
          return;
        }
        setState({ phase: "done", report: data.report, unknownHeaders: data.parse?.unknownHeaders ?? [] });
      } catch {
        setState({ phase: "error", message: "Network error — please try again." });
      }
    },
    [region],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (file) void upload(file);
    },
    [upload],
  );

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <label className="muted">Marketplace region:&nbsp;</label>
        <select
          value={region}
          onChange={(e) => setRegion(e.target.value)}
          style={{ background: "var(--panel-2)", color: "var(--text)", border: "1px solid var(--border)", borderRadius: 8, padding: "8px 10px" }}
        >
          <option value="US">United States (USD)</option>
          <option value="GB">United Kingdom (GBP)</option>
        </select>
      </div>

      <div
        className={`dropzone ${dragging ? "drag" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        {state.phase === "uploading" ? (
          <p>Auditing your statements…</p>
        ) : (
          <>
            <p style={{ fontSize: "1.1rem", margin: 0 }}>Drop your settlement export here</p>
            <p className="muted">or click to choose a .xlsx / .csv file (max 15 MB)</p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls,.csv"
          hidden
          onChange={(e) => { const f = e.target.files?.[0]; if (f) void upload(f); }}
        />
      </div>

      {state.phase === "error" && (
        <div className="panel mt" style={{ borderColor: "var(--danger)" }}>
          <strong style={{ color: "var(--danger)" }}>Couldn&apos;t audit this file</strong>
          <p className="muted">{state.message}</p>
          {state.unknownHeaders && state.unknownHeaders.length > 0 && (
            <p className="muted">Unrecognized columns: {state.unknownHeaders.join(", ")}</p>
          )}
        </div>
      )}

      {state.phase === "done" && <ReportView report={state.report} unknownHeaders={state.unknownHeaders} />}
    </div>
  );
}

function ReportView({ report, unknownHeaders }: { report: AuditReport; unknownHeaders: string[] }) {
  const [email, setEmail] = useState("");
  const [captured, setCaptured] = useState(false);

  async function submitLead(e: React.FormEvent) {
    e.preventDefault();
    await fetch("/api/lead", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, rows: report.transactionsChecked, owedCents: report.totalOwedCents }),
    }).catch(() => {});
    setCaptured(true);
  }

  function downloadCsv() {
    const header = ["check", "order_id", "fee_type", "amount_owed", "severity", "detail"];
    const lines = report.topFindings.map((f) =>
      [f.checkId, f.orderId ?? "", "", (f.deltaCents / 100).toFixed(2), f.severity, csvCell(f.message)].join(","),
    );
    const csv = [header.join(","), ...lines].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "payoutproof-findings.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="mt">
      <div className="panel">
        <p className="result-headline">
          {report.totalOwedCents > 0 ? (
            <>
              We found <span className="owed">{report.totalOwedFormatted}</span> TikTok Shop may owe you
            </>
          ) : (
            report.headline
          )}
        </p>
        <p className="muted">
          Checked {report.transactionsChecked.toLocaleString()} transactions · {report.discrepancyCount} findings
        </p>

        {report.sections.length > 0 && (
          <table className="mt">
            <thead>
              <tr><th>Issue</th><th>Count</th><th style={{ textAlign: "right" }}>Amount owed</th></tr>
            </thead>
            <tbody>
              {report.sections.map((s) => (
                <tr key={s.checkId}>
                  <td>{s.label}</td>
                  <td>{s.count}</td>
                  <td style={{ textAlign: "right" }} className="owed">{s.owedFormatted}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {report.topFindings.length > 0 && (
        <div className="panel mt">
          <h3>Top findings</h3>
          {report.topFindings.map((f, i) => (
            <div className="finding" key={i}>
              <div>
                <div>{f.label}{f.orderId ? ` · order ${f.orderId}` : ""}</div>
                <div className="meta">{f.message}</div>
              </div>
              <div style={{ whiteSpace: "nowrap" }}>
                <span className={`badge ${f.severity}`}>{f.severity}</span>{" "}
                <strong className="owed">{f.deltaFormatted}</strong>
              </div>
            </div>
          ))}
        </div>
      )}

      {report.topFindings.length > 0 && (
        <div className="panel mt center">
          {captured ? (
            <>
              <h3>Your findings are ready</h3>
              <p className="muted">Download the top findings, or automate this on every payout.</p>
              <button className="btn" onClick={downloadCsv}>Download findings CSV</button>{" "}
              <a href="/pricing" className="btn secondary">Automate it</a>
            </>
          ) : (
            <>
              <h3>Get your findings + full evidence pack</h3>
              <p className="muted">
                Enter your email to download the findings and get a free guide on recovering
                them from TikTok seller support.
              </p>
              <form onSubmit={submitLead} style={{ maxWidth: 380, margin: "0 auto" }}>
                <input
                  type="email"
                  required
                  placeholder="you@store.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
                <button className="btn mt" type="submit" style={{ width: "100%" }}>
                  Show my findings
                </button>
              </form>
            </>
          )}
        </div>
      )}

      <div className="panel mt center">
        <h3>Want this run automatically on every payout?</h3>
        <p className="muted">
          Connect your shop and PayoutProof audits each settlement as it posts, tracks what
          you recover, and generates a worksheet for TikTok seller support.
        </p>
        <a href="/pricing" className="btn">Start a 14-day free trial</a>
      </div>

      {unknownHeaders.length > 0 && (
        <p className="muted mt center">
          Note: {unknownHeaders.length} column(s) in your file weren&apos;t recognized and were
          ignored. Connect your shop for full coverage.
        </p>
      )}
    </div>
  );
}

function csvCell(value: string): string {
  return /[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
}
