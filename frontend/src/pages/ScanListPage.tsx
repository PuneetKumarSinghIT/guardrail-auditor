import { Link } from "react-router-dom";
import { AppHeader } from "../components/AppHeader";
import { ScanUploader } from "../components/ScanUploader";
import { useScans } from "../hooks/useScans";
import { riskBand, statusStyle } from "../lib/risk";
import type { ScanSummary } from "../lib/types";

function formatDate(iso: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export function ScanListPage() {
  const { data: scans, isLoading, isError } = useScans();

  return (
    <div className="min-h-full">
      <AppHeader />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <section className="mb-8">
          <h2 className="mb-3 text-lg font-semibold text-slate-900">
            Upload a new file
          </h2>
          <ScanUploader />
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-slate-900">Scans</h2>

          {isLoading && <p className="text-sm text-slate-500">Loading scans…</p>}
          {isError && (
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
              Failed to load scans.
            </p>
          )}

          {scans && scans.length === 0 && (
            <p className="rounded-lg border border-dashed border-slate-300 bg-white px-4 py-8 text-center text-sm text-slate-400">
              No scans yet — upload an IaC file above to get started.
            </p>
          )}

          {scans && scans.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-3">File</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Risk score</th>
                    <th className="px-4 py-3">Created</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {scans.map((s) => (
                    <ScanRow key={s.scan_job_id} scan={s} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

function ScanRow({ scan }: { scan: ScanSummary }) {
  const status = statusStyle(scan.status);
  const band = riskBand(scan.risk_score ?? 0);

  return (
    <tr className="hover:bg-slate-50">
      <td className="px-4 py-3 font-medium text-slate-800">{scan.file_name}</td>
      <td className="px-4 py-3">
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${status.className}`}
        >
          {status.label}
        </span>
      </td>
      <td className="px-4 py-3">
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold ${band.bgClass} ${band.textClass}`}
        >
          {scan.risk_score ?? 0}
        </span>
      </td>
      <td className="px-4 py-3 text-slate-500">{formatDate(scan.created_at)}</td>
      <td className="px-4 py-3 text-right">
        <Link
          to={`/scans/${scan.scan_job_id}`}
          className="text-xs font-semibold text-blue-600 hover:underline"
        >
          View Report →
        </Link>
      </td>
    </tr>
  );
}
