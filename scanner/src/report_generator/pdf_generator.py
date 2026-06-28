"""PDF report generation (reportlab).

Pure function: given a scan_job dict + a flat list of finding dicts (all
severities), produce a self-contained PDF as bytes. The caller (report_handler)
uploads the bytes to S3. No AWS calls live here — this stays unit-testable with
no mocks.

Layout (top to bottom):
  1. Cover            — file name, scan date, risk score + label
  2. Executive Summary — finding counts by severity, compliant-resource note
  3. CRITICAL findings  (one row per finding, AI explanation inline)
  4. HIGH findings
  5. MEDIUM findings
  6. LOW findings

The email body only ever shows CRITICAL + HIGH; the PDF is the ONLY place the
full detail (every severity) appears — see CLAUDE.md Phase 9 email spec.
"""
from __future__ import annotations

import io
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Severity render order — CRITICAL first, matching dashboard + email priority.
SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
_SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITY_ORDER)}

_SEVERITY_COLOR = {
    "CRITICAL": colors.HexColor("#7f1d1d"),
    "HIGH": colors.HexColor("#b91c1c"),
    "MEDIUM": colors.HexColor("#d97706"),
    "LOW": colors.HexColor("#15803d"),
}


def _risk_label(score: int) -> str:
    """Mirror the dashboard's 4 colour bands (CLAUDE.md Risk Score Algorithm)."""
    if score <= 30:
        return "Low Risk"
    if score <= 60:
        return "Medium Risk"
    if score <= 80:
        return "High Risk"
    return "Critical Risk"


def _as_int(value: Any, default: int = 0) -> int:
    """DynamoDB numbers come back as Decimal; normalise to int safely."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _sort_findings(findings: list[dict]) -> list[dict]:
    """CRITICAL first, then by rule_id for a stable, readable order."""
    return sorted(
        findings,
        key=lambda f: (
            _SEVERITY_RANK.get(f.get("severity", "LOW"), len(SEVERITY_ORDER)),
            str(f.get("rule_id", "")),
        ),
    )


def _count_by_severity(findings: list[dict]) -> dict[str, int]:
    counts = {s: 0 for s in SEVERITY_ORDER}
    for f in findings:
        sev = f.get("severity", "LOW")
        counts[sev] = counts.get(sev, 0) + 1
    return counts


def generate(scan_job: dict, findings: list[dict]) -> bytes:
    """Render the full PDF report and return it as bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        title="Security Guardrail Auditor Report",
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CoverTitle", parent=styles["Title"], fontSize=24, spaceAfter=18
    )
    h2 = ParagraphStyle("Section", parent=styles["Heading2"], spaceBefore=16, spaceAfter=8)
    body = ParagraphStyle("Body", parent=styles["BodyText"], alignment=TA_LEFT)

    file_name = scan_job.get("file_name", "unknown")
    created_at = scan_job.get("created_at", "")
    risk_score = _as_int(scan_job.get("risk_score", 0))
    sorted_findings = _sort_findings(findings)
    counts = _count_by_severity(findings)

    elements: list[Any] = []

    # ── 1. Cover ──────────────────────────────────────────────────────────────
    elements.append(Paragraph("Security Guardrail Auditor", title_style))
    elements.append(Paragraph("Infrastructure-as-Code Security Report", styles["Heading3"]))
    elements.append(Spacer(1, 0.3 * inch))
    cover_rows = [
        ["File", file_name],
        ["Scan date", str(created_at)],
        ["Risk score", f"{risk_score}/100  ({_risk_label(risk_score)})"],
        ["Total findings", str(len(findings))],
    ]
    cover_table = Table(cover_rows, colWidths=[1.6 * inch, 4.4 * inch])
    cover_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
            ]
        )
    )
    elements.append(cover_table)

    # ── 2. Executive Summary ──────────────────────────────────────────────────
    elements.append(Paragraph("Executive Summary", h2))
    summary_rows = [["Severity", "Count"]]
    for sev in SEVERITY_ORDER:
        summary_rows.append([sev, str(counts.get(sev, 0))])
    summary_table = Table(summary_rows, colWidths=[3 * inch, 3 * inch])
    summary_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]
    for row_idx, sev in enumerate(SEVERITY_ORDER, start=1):
        summary_style.append(
            ("TEXTCOLOR", (0, row_idx), (0, row_idx), _SEVERITY_COLOR[sev])
        )
    summary_table.setStyle(TableStyle(summary_style))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(
        Paragraph(
            "All findings below are grouped by severity, most severe first. "
            "Resources not listed passed every enabled rule.",
            body,
        )
    )

    # ── 3-6. Findings grouped by severity ─────────────────────────────────────
    for sev in SEVERITY_ORDER:
        sev_findings = [f for f in sorted_findings if f.get("severity") == sev]
        if not sev_findings:
            continue
        elements.append(Paragraph(f"{sev} Findings ({len(sev_findings)})", h2))
        for f in sev_findings:
            rule_id = f.get("rule_id", "")
            resource = f.get("resource_name", "")
            line = _as_int(f.get("line_number", 0))
            heading = f"<b>{rule_id}</b> &mdash; {resource} (line {line})"
            elements.append(Paragraph(heading, body))
            explanation = f.get("ai_explanation") or "No AI explanation available."
            elements.append(Paragraph(explanation, body))
            fix_code = f.get("ai_fix_code")
            if fix_code:
                elements.append(Paragraph("<b>Suggested fix:</b>", body))
                elements.append(Paragraph(_escape_code(fix_code), styles["Code"]))
            elements.append(Spacer(1, 0.12 * inch))

    doc.build(elements)
    return buffer.getvalue()


def _escape_code(code: str) -> str:
    """reportlab Paragraph parses a tiny HTML subset — escape the dangerous few
    so code snippets (which contain <, >, &) render literally."""
    return (
        code.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )
