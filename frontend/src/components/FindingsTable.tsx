import { useMemo, useState } from "react";
import type { Finding, Severity } from "../lib/types";
import { hasFix, severityBadgeClass, sortBySeverity } from "../lib/risk";

interface FindingsTableProps {
  findings: Finding[];
  onSelect: (finding: Finding) => void;
}

const FILTERS: (Severity | "ALL")[] = [
  "ALL",
  "CRITICAL",
  "HIGH",
  "MEDIUM",
  "LOW",
];

// Sortable findings table — CRITICAL first by default, with a severity filter
// bar. Row click opens the AI explanation drawer.
export function FindingsTable({ findings, onSelect }: FindingsTableProps) {
  const [filter, setFilter] = useState<Severity | "ALL">("ALL");

  const rows = useMemo(() => {
    const sorted = sortBySeverity(findings);
    return filter === "ALL"
      ? sorted
      : sorted.filter((f) => f.severity === filter);
  }, [findings, filter]);

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded-full px-3 py-1 text-xs font-semibold ${
              filter === f
                ? "bg-blue-600 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">Rule</th>
              <th className="px-4 py-3">Resource</th>
              <th className="px-4 py-3">Line</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((f) => (
              <tr
                key={f.finding_id}
                onClick={() => onSelect(f)}
                className="cursor-pointer hover:bg-slate-50"
              >
                <td className="px-4 py-3">
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-bold ${severityBadgeClass(
                      f.severity
                    )}`}
                  >
                    {f.severity}
                  </span>
                </td>
                <td className="px-4 py-3 font-mono text-xs font-semibold text-slate-700">
                  {f.rule_id}
                </td>
                <td className="px-4 py-3 text-slate-800">{f.resource_name}</td>
                <td className="px-4 py-3 tabular-nums text-slate-500">
                  {f.line_number ?? "—"}
                </td>
                <td className="px-4 py-3 text-slate-500">{f.category ?? "—"}</td>
                <td className="px-4 py-3 text-right">
                  <span className="text-xs font-medium text-blue-600">
                    {hasFix(f) ? "View Fix →" : "Details →"}
                  </span>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td
                  colSpan={6}
                  className="px-4 py-8 text-center text-slate-400"
                >
                  No findings for this filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
