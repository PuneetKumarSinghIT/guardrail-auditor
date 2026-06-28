"""Email construction + SES delivery.

Two email shapes, both returned as MIMEMultipart so the handler just calls
send_email():

  build_success_email — CRITICAL + HIGH findings only in the body, PDF attached.
  build_failure_email — plain text, debug pointers, NO attachment (no report exists).

Per CLAUDE.md Phase 9 email spec, the success body deliberately omits MEDIUM/LOW
findings and all compliant resources — full detail lives only in the PDF.
"""
from __future__ import annotations

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import boto3

# Body shows only these severities, in this order.
BODY_SEVERITIES = ["CRITICAL", "HIGH"]
_SEVERITY_RANK = {s: i for i, s in enumerate(BODY_SEVERITIES)}

ses_client = boto3.client("ses")


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _risk_label(score: int) -> str:
    if score <= 30:
        return "Low Risk"
    if score <= 60:
        return "Medium Risk"
    if score <= 80:
        return "High Risk"
    return "Critical Risk"


def _crit_high(findings: list[dict]) -> list[dict]:
    """Filter to CRITICAL+HIGH and sort CRITICAL first. The single chokepoint
    that guarantees MEDIUM/LOW never reach the email body."""
    filtered = [f for f in findings if f.get("severity") in BODY_SEVERITIES]
    return sorted(
        filtered,
        key=lambda f: (_SEVERITY_RANK[f["severity"]], str(f.get("rule_id", ""))),
    )


def build_success_email(
    scan_job: dict,
    findings: list[dict],
    pdf_bytes: bytes,
    cloudfront_url: str,
    from_addr: str,
    to_addr: str,
) -> MIMEMultipart:
    """Scan-complete email: CRITICAL/HIGH summary + PDF attachment."""
    file_name = scan_job.get("file_name", "unknown")
    scan_job_id = scan_job.get("scan_job_id", "")
    risk_score = _as_int(scan_job.get("risk_score", 0))

    relevant = _crit_high(findings)
    counts = scan_job.get("finding_counts", {}) or {}
    critical_count = _as_int(counts.get("CRITICAL", sum(1 for f in relevant if f["severity"] == "CRITICAL")))
    high_count = _as_int(counts.get("HIGH", sum(1 for f in relevant if f["severity"] == "HIGH")))

    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"Scan Complete: {file_name} — Risk Score {risk_score}/100"
    msg["From"] = from_addr
    msg["To"] = to_addr

    lines = [
        f"Your IaC file '{file_name}' has been scanned.",
        f"Risk Score: {risk_score}/100 ({_risk_label(risk_score)})",
        "",
        f"Issues Requiring Attention ({critical_count} CRITICAL, {high_count} HIGH):",
        "─────────────────────────────────────────",
    ]
    if relevant:
        for f in relevant:
            lines.append(
                f"[{f.get('severity')}] {f.get('rule_id')} — "
                f"{f.get('resource_name')} (line {_as_int(f.get('line_number', 0))})"
            )
    else:
        lines.append("No CRITICAL or HIGH findings. Nice work.")
    lines += [
        "─────────────────────────────────────────",
        "MEDIUM and LOW findings, and all compliant resources, are in the attached PDF.",
        f"View full report: {cloudfront_url}/scans/{scan_job_id}",
    ]
    body_text = "\n".join(lines)

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(body_text, "plain", "utf-8"))
    alt.attach(MIMEText(_html_body(body_text), "html", "utf-8"))
    msg.attach(alt)

    attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
    attachment.add_header(
        "Content-Disposition", "attachment", filename=f"{scan_job_id}-report.pdf"
    )
    msg.attach(attachment)
    return msg


def build_failure_email(scan_job: dict, env: str, from_addr: str, to_addr: str) -> MIMEMultipart:
    """Scan-failed email: plain text, debug pointers, NO PDF (none was made)."""
    file_name = scan_job.get("file_name", "unknown")
    scan_job_id = scan_job.get("scan_job_id", "")
    failed_stage = scan_job.get("failed_stage", "unknown")
    error_message = scan_job.get("error_message", "")
    trace_id = scan_job.get("trace_id", "")

    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"SCAN FAILED: {file_name} — Developer Attention Required"
    msg["From"] = from_addr
    msg["To"] = to_addr

    body_text = "\n".join(
        [
            f"File: {file_name} | Scan ID: {scan_job_id}",
            f"Failed at: {failed_stage}",
            f"Error: {error_message}",
            "",
            "Debug:",
            f"  CloudWatch Logs: /guardrail/{env}/ecs/{failed_stage}",
            f"  X-Ray Trace: {trace_id}",
            f"  DynamoDB: scan-jobs-{env} PK={scan_job_id}",
            "",
            "No report was generated. Resubmit after the bug is fixed.",
        ]
    )
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    return msg


def send_email(mime_msg: MIMEMultipart, from_addr: str, to_addr: str) -> dict:
    """Deliver a pre-built MIME message via SES send_raw_email."""
    return ses_client.send_raw_email(
        Source=from_addr,
        Destinations=[to_addr],
        RawMessage={"Data": mime_msg.as_string()},
    )


def _html_body(text: str) -> str:
    """Wrap the plain-text body in a <pre> block — keeps alignment, zero deps."""
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        '<html><body style="font-family:monospace;font-size:14px;">'
        f"<pre>{escaped}</pre></body></html>"
    )
