"""Tests for the email layer — success (CRITICAL/HIGH + PDF) and failure paths.

The body/attachment rules (CLAUDE.md Phase 9 email spec) are tested directly
against email_service.build_* (pure, deterministic). Two moto-backed handler
tests exercise the runtime routing + SES send for coverage.
"""
import json
import os
from unittest.mock import patch

import boto3
from moto import mock_aws

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("SCAN_JOBS_TABLE", "scan-jobs-test")
os.environ.setdefault("FINDINGS_TABLE", "findings-test")
os.environ.setdefault("REPORTS_BUCKET", "guardrail-scan-reports-test")
os.environ.setdefault("CLOUDFRONT_URL", "https://dash.example.com")
os.environ.setdefault("APP_SECRETS_ARN", "guardrail/test/app-secrets")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("EVENT_BUS_NAME", "default")

from src.services import email_service
from src.handlers import email_handler

FROM = "puneetkumarsingh765@gmail.com"
TO = "puneetkumarsingh765@gmail.com"


def _all_severity_findings():
    return [
        {"rule_id": "S3-001", "severity": "CRITICAL", "resource_name": "aws_s3_bucket.b", "line_number": 12},
        {"rule_id": "IAM-001", "severity": "HIGH", "resource_name": "aws_iam_policy.admin", "line_number": 8},
        {"rule_id": "S3-003", "severity": "MEDIUM", "resource_name": "aws_s3_bucket.c", "line_number": 20},
        {"rule_id": "S3-005", "severity": "LOW", "resource_name": "aws_s3_bucket.d", "line_number": 30},
    ]


def _job():
    return {
        "scan_job_id": "job-email",
        "file_name": "demo.tf",
        "risk_score": 72,
        "finding_counts": {"CRITICAL": 1, "HIGH": 1, "MEDIUM": 1, "LOW": 1},
    }


def _plain_text(msg) -> str:
    for part in msg.walk():
        if part.get_content_type() == "text/plain":
            return part.get_payload(decode=True).decode("utf-8")
    return ""


def _has_pdf_attachment(msg) -> bool:
    for part in msg.walk():
        if part.get_content_type() == "application/pdf":
            return True
    return False


# ── Success body rules ───────────────────────────────────────────────────────
def test_success_body_has_critical_and_high():
    msg = email_service.build_success_email(_job(), _all_severity_findings(), b"%PDF-x", "https://d", FROM, TO)
    body = _plain_text(msg)
    assert "[CRITICAL] S3-001" in body
    assert "[HIGH] IAM-001" in body
    assert "Risk Score 72/100" in msg["Subject"]


def test_success_body_excludes_medium_low():
    msg = email_service.build_success_email(_job(), _all_severity_findings(), b"%PDF-x", "https://d", FROM, TO)
    body = _plain_text(msg)
    assert "S3-003" not in body  # MEDIUM excluded
    assert "S3-005" not in body  # LOW excluded
    assert "MEDIUM" not in body.split("Issues Requiring Attention")[1].split("─────")[1]


def test_success_pdf_attached():
    msg = email_service.build_success_email(_job(), _all_severity_findings(), b"%PDF-bytes", "https://d", FROM, TO)
    assert _has_pdf_attachment(msg)
    for part in msg.walk():
        if part.get_content_type() == "application/pdf":
            assert part.get_filename() == "job-email-report.pdf"


# ── Failure body rules ───────────────────────────────────────────────────────
def test_failure_subject_contains_failed():
    job = {"scan_job_id": "job-x", "file_name": "demo.tf", "failed_stage": "rules-engine", "error_message": "boom"}
    msg = email_service.build_failure_email(job, "dev", FROM, TO)
    assert "SCAN FAILED" in msg["Subject"]


def test_failure_body_has_stage_and_error():
    job = {"scan_job_id": "job-x", "file_name": "demo.tf", "failed_stage": "rules-engine", "error_message": "boom (exitCode=1)"}
    msg = email_service.build_failure_email(job, "dev", FROM, TO)
    body = _plain_text(msg)
    assert "Failed at: rules-engine" in body
    assert "boom (exitCode=1)" in body


def test_failure_no_attachment():
    job = {"scan_job_id": "job-x", "file_name": "demo.tf", "failed_stage": "checkov", "error_message": "boom"}
    msg = email_service.build_failure_email(job, "dev", FROM, TO)
    assert not _has_pdf_attachment(msg)


# ── Handler routing (moto-backed) ────────────────────────────────────────────
def _setup_aws():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    jobs = ddb.create_table(
        TableName="scan-jobs-test",
        KeySchema=[{"AttributeName": "scan_job_id", "KeyType": "HASH"}, {"AttributeName": "created_at", "KeyType": "RANGE"}],
        AttributeDefinitions=[{"AttributeName": "scan_job_id", "AttributeType": "S"}, {"AttributeName": "created_at", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    ddb.create_table(
        TableName="findings-test",
        KeySchema=[{"AttributeName": "scan_job_id", "KeyType": "HASH"}, {"AttributeName": "finding_id", "KeyType": "RANGE"}],
        AttributeDefinitions=[{"AttributeName": "scan_job_id", "AttributeType": "S"}, {"AttributeName": "finding_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    sm = boto3.client("secretsmanager", region_name="us-east-1")
    sm.create_secret(
        Name="guardrail/test/app-secrets",
        SecretString=json.dumps({"ses_from_email": FROM, "ses_to_email": TO}),
    )
    ses = boto3.client("ses", region_name="us-east-1")
    ses.verify_email_identity(EmailAddress=FROM)
    return ddb, jobs


@mock_aws
def test_handler_success_routes_and_sends():
    email_handler.get_secrets.cache_clear()
    ddb, jobs = _setup_aws()
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="guardrail-scan-reports-test")
    s3.put_object(Bucket="guardrail-scan-reports-test", Key="job-email/report.pdf", Body=b"%PDF-data")
    jobs.put_item(Item={
        "scan_job_id": "job-email", "created_at": "2026-06-28T00:00:00+00:00",
        "status": "REPORT_COMPLETE", "file_name": "demo.tf", "risk_score": 72,
        "report_s3_key": "job-email/report.pdf",
        "finding_counts": {"CRITICAL": 1, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
    })

    with patch.object(email_service, "send_email", return_value={"MessageId": "ok"}) as se:
        result = email_handler.handler(
            {"detail-type": "ReportGenerated", "detail": {"scan_job_id": "job-email"}}, None
        )
    assert result == {"statusCode": 200, "email_type": "success"}
    assert se.called


@mock_aws
def test_handler_failure_routes_and_sends():
    email_handler.get_secrets.cache_clear()
    ddb, jobs = _setup_aws()
    jobs.put_item(Item={
        "scan_job_id": "job-fail", "created_at": "2026-06-28T00:00:00+00:00",
        "status": "FAILED", "file_name": "demo.tf", "failed_stage": "rules-engine",
        "error_message": "crash (exitCode=1)",
    })

    with patch.object(email_service, "send_email", return_value={"MessageId": "ok"}) as se:
        result = email_handler.handler(
            {"detail-type": "ScanFailed", "detail": {"scan_job_id": "job-fail"}}, None
        )
    assert result == {"statusCode": 200, "email_type": "failure"}
    assert se.called
