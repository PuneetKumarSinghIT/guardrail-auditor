// Pure presentation logic for risk scores and finding severities.
// Kept dependency-free so it can be unit-tested without rendering.

import type { Finding, ScanStatus, Severity } from "./types";

export interface RiskBand {
  label: string;
  // Tailwind text/bg/ring color class fragments
  color: string; // hex for SVG stroke
  textClass: string;
  bgClass: string;
}

// Thresholds match CLAUDE.md Risk Score Algorithm:
//   0-30 green | 31-60 amber | 61-80 red | 81-100 dark red
export function riskBand(score: number): RiskBand {
  if (score <= 30)
    return {
      label: "Low Risk",
      color: "#16a34a",
      textClass: "text-green-700",
      bgClass: "bg-green-100",
    };
  if (score <= 60)
    return {
      label: "Medium Risk",
      color: "#d97706",
      textClass: "text-amber-700",
      bgClass: "bg-amber-100",
    };
  if (score <= 80)
    return {
      label: "High Risk",
      color: "#dc2626",
      textClass: "text-red-700",
      bgClass: "bg-red-100",
    };
  return {
    label: "Critical Risk",
    color: "#7f1d1d",
    textClass: "text-red-100",
    bgClass: "bg-red-900",
  };
}

const SEVERITY_RANK: Record<Severity, number> = {
  CRITICAL: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
};

// Sort findings CRITICAL → HIGH → MEDIUM → LOW (stable on rule_id as tiebreaker).
export function sortBySeverity(findings: Finding[]): Finding[] {
  return [...findings].sort((a, b) => {
    const rank =
      (SEVERITY_RANK[a.severity] ?? 99) - (SEVERITY_RANK[b.severity] ?? 99);
    if (rank !== 0) return rank;
    return (a.rule_id ?? "").localeCompare(b.rule_id ?? "");
  });
}

export function severityBadgeClass(severity: Severity): string {
  switch (severity) {
    case "CRITICAL":
      return "bg-red-900 text-red-100";
    case "HIGH":
      return "bg-red-100 text-red-700";
    case "MEDIUM":
      return "bg-amber-100 text-amber-700";
    case "LOW":
      return "bg-slate-200 text-slate-700";
    default:
      return "bg-slate-200 text-slate-700";
  }
}

// CRITICAL/HIGH findings get an AI-generated fix; MEDIUM/LOW are skipped by the
// Phase 6 cost guard, so only show the "View Fix" affordance for those two.
export function hasFix(finding: Finding): boolean {
  return (
    (finding.severity === "CRITICAL" || finding.severity === "HIGH") &&
    !!finding.ai_fix_code
  );
}

export interface StatusStyle {
  label: string;
  className: string;
}

export function statusStyle(status: ScanStatus): StatusStyle {
  switch (status) {
    case "QUEUED":
      return { label: "Queued", className: "bg-slate-200 text-slate-700" };
    case "SCANNING":
      return { label: "Scanning", className: "bg-blue-100 text-blue-700" };
    case "AI_ANALYSIS":
      return { label: "AI Analysis", className: "bg-purple-100 text-purple-700" };
    case "AI_COMPLETE":
      return { label: "AI Analysis", className: "bg-purple-100 text-purple-700" };
    case "COMPLETE":
      return { label: "Complete", className: "bg-green-100 text-green-700" };
    case "FAILED":
      return { label: "Failed", className: "bg-red-100 text-red-700" };
    default:
      return { label: status, className: "bg-slate-200 text-slate-700" };
  }
}
