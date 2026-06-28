import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AppHeader } from "../components/AppHeader";
import { RiskScoreMeter } from "../components/RiskScoreMeter";
import { FindingsTable } from "../components/FindingsTable";
import { AiExplanationPanel } from "../components/AiExplanationPanel";
import { useReportUrl, useScan } from "../hooks/useScans";
import { statusStyle } from "../lib/risk";
import type { Finding, Severity } from "../lib/types";

const COUNT_ORDER: Severity[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
const COUNT_STYLE: Record<Severity, string> = {
  CRITICAL: "bg-red-900 text-red-100",
  HIGH: "bg-red-100 text-red-700",
  MEDIUM: "bg-amber-100 text-amber-700",
  LOW: "bg-slate-200 text-slate-700",
};

export function ScanDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: scan, isLoading, isError } = useScan(id);
  const [selected, setSelected] = useState<Finding | null>(null);
  const [wantReport, setWantReport] = useState(false);

  const report = useReportUrl(id, wantReport);

  // When the user clicks Download and the presigned URL resolves, trigger the
  // download via a programmatic anchor click. NOTE: window.open() here was
  // unreliable — it runs in a useEffect (an async continuation, not the click's
  // user-gesture stack), so browser popup blockers silently killed it ("download
  // does nothing"). An anchor click is treated as a download, not a popup, so it
  // is not blocked. The API's presigned URL sets Content-Disposition: attachment,
  // so S3 serves it as a named .pdf download (the cross-origin `download` attr is
  // ignored, hence the server-side header).
  useEffect(() => {
    if (wantReport && report.data?.report_url) {
      const a = document.createElement("a");
      a.href = report.data.report_url;
      a.rel = "noopener";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setWantReport(false);
    }
  }, [wantReport, report.data]);

  return (
    <div className="min-h-full">
      <AppHeader />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Link
          to="/scans"
          className="text-sm font-medium text-blue-600 hover:underline"
        >
          ← Back to scans
        </Link>

        {isLoading && (
          <p className="mt-6 text-sm text-slate-500">Loading scan…</p>
        )}
        {isError && (
          <p className="mt-6 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            Failed to load this scan.
          </p>
        )}

        {scan && (
          <>
            <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
              <div>
                <h1 className="text-2xl font-bold text-slate-900">
                  {scan.file_name}
                </h1>
                <div className="mt-1 flex items-center gap-3 text-sm text-slate-500">
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                      statusStyle(scan.status).className
                    }`}
                  >
                    {statusStyle(scan.status).label}
                  </span>
                  <span>{new Date(scan.created_at).toLocaleString()}</span>
                </div>
              </div>

              <button
                onClick={() => setWantReport(true)}
                disabled={report.isFetching && wantReport}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {report.isFetching && wantReport
                  ? "Preparing…"
                  : "Download PDF Report"}
              </button>
            </div>

            {wantReport && report.isError && (
              <p className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-700">
                The PDF report isn't ready yet. It's generated after AI analysis
                completes.
              </p>
            )}

            <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-3">
              <div className="flex items-center justify-center rounded-xl border border-slate-200 bg-white p-6">
                <RiskScoreMeter score={scan.risk_score ?? 0} />
              </div>

              <div className="lg:col-span-2">
                <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
                  Findings by severity
                </h2>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {COUNT_ORDER.map((sev) => (
                    <div
                      key={sev}
                      className={`rounded-lg p-4 text-center ${COUNT_STYLE[sev]}`}
                    >
                      <div className="text-2xl font-bold tabular-nums">
                        {scan.finding_counts?.[sev] ?? 0}
                      </div>
                      <div className="text-xs font-semibold uppercase">
                        {sev}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <section className="mt-8">
              <h2 className="mb-3 text-lg font-semibold text-slate-900">
                All findings
              </h2>
              <FindingsTable
                findings={scan.findings ?? []}
                onSelect={setSelected}
              />
            </section>
          </>
        )}
      </main>

      <AiExplanationPanel
        finding={selected}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}
