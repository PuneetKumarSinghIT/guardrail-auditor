"""Tests for the reportlab PDF generator (pure — no AWS)."""
from decimal import Decimal

from src.report_generator import pdf_generator


def _findings():
    return [
        {"rule_id": "S3-005", "severity": "LOW", "resource_name": "b1", "resource_type": "aws_s3_bucket", "line_number": 5, "ai_explanation": "low"},
        {"rule_id": "S3-001", "severity": "CRITICAL", "resource_name": "b2", "resource_type": "aws_s3_bucket", "line_number": 1, "ai_explanation": "crit", "ai_fix_code": "acl = \"private\""},
        {"rule_id": "ENC-001", "severity": "HIGH", "resource_name": "v1", "resource_type": "aws_ebs_volume", "line_number": 9, "ai_explanation": "high"},
        {"rule_id": "S3-003", "severity": "MEDIUM", "resource_name": "b3", "resource_type": "aws_s3_bucket", "line_number": 7, "ai_explanation": "med"},
    ]


def _job():
    return {
        "scan_job_id": "job-pdf",
        "file_name": "demo-master-bad.tf",
        "created_at": "2026-06-28T00:00:00+00:00",
        "risk_score": Decimal("72"),
        "finding_counts": {"CRITICAL": 1, "HIGH": 1, "MEDIUM": 1, "LOW": 1},
    }


def test_generate_returns_pdf_bytes():
    pdf = pdf_generator.generate(_job(), _findings())
    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000
    assert pdf.startswith(b"%PDF")  # valid PDF magic header


def test_all_severity_sections_counted():
    counts = pdf_generator._count_by_severity(_findings())
    assert counts == {"CRITICAL": 1, "HIGH": 1, "MEDIUM": 1, "LOW": 1}
    # Empty severities still render a complete report without crashing.
    pdf = pdf_generator.generate(_job(), [_findings()[1]])  # CRITICAL only
    assert pdf.startswith(b"%PDF")


def test_critical_sorted_first():
    ordered = pdf_generator._sort_findings(_findings())
    assert ordered[0]["severity"] == "CRITICAL"
    assert [f["severity"] for f in ordered] == ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    # Risk label bands match the dashboard thresholds.
    assert pdf_generator._risk_label(72) == "High Risk"
    assert pdf_generator._risk_label(20) == "Low Risk"
