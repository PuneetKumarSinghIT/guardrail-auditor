// Shared API types — mirror the shapes returned by the Phase 7 REST API.

export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export type ScanStatus =
  | "QUEUED"
  | "SCANNING"
  | "AI_ANALYSIS"
  | "AI_COMPLETE"
  | "COMPLETE"
  | "REPORT_COMPLETE"
  | "FAILED";

export interface FindingCounts {
  CRITICAL?: number;
  HIGH?: number;
  MEDIUM?: number;
  LOW?: number;
}

// GET /v1/scans — list item (summary fields only)
export interface ScanSummary {
  scan_job_id: string;
  file_name: string;
  status: ScanStatus;
  risk_score: number;
  finding_counts: FindingCounts;
  created_at: string;
}

export interface Finding {
  finding_id: string;
  scan_job_id: string;
  rule_id: string;
  severity: Severity;
  resource_name: string;
  resource_type?: string;
  line_number?: number;
  code_snippet?: string;
  ai_explanation?: string;
  ai_fix_code?: string;
  category?: string;
}

// GET /v1/scans/{id} — full detail + findings
export interface ScanDetail extends ScanSummary {
  s3_key?: string;
  iac_type?: string;
  report_s3_key?: string;
  findings: Finding[];
}

// POST /v1/scans — presigned upload response
export interface CreateScanResponse {
  scan_job_id: string;
  presigned_url: string;
  status: ScanStatus;
}

// GET /v1/scans/{id}/report
export interface ReportUrlResponse {
  report_url: string;
  expires_in: number;
}
