"""Email Lambda — sends the scan-complete OR scan-failed notification via SES.

ONE Lambda, TWO EventBridge rules point at it. EventBridge cannot inject env
vars into a Lambda target, so the path is chosen at runtime from the event's
detail-type (with the EMAIL_TYPE env var as the fallback default):

  ReportGenerated  -> success path: CRITICAL/HIGH summary + PDF attachment
  ScanFailed       -> failure path: plain-text debug email, no attachment

Secrets (the SES From/To addresses — PII) are fetched once at cold start from
Secrets Manager; everything else is a plain env var (CLAUDE.md secrets policy).
"""
import json
import logging
import os
from functools import lru_cache

import boto3
from boto3.dynamodb.conditions import Key as DdbKey

from src.services import email_service

# ── Plain env vars ───────────────────────────────────────────────────────────
SCAN_JOBS_TABLE = os.environ["SCAN_JOBS_TABLE"]
FINDINGS_TABLE = os.environ["FINDINGS_TABLE"]
REPORTS_BUCKET = os.environ["REPORTS_BUCKET"]
CLOUDFRONT_URL = os.environ.get("CLOUDFRONT_URL", "")
ENV = os.environ.get("ENVIRONMENT", "dev")
EMAIL_TYPE_DEFAULT = os.environ.get("EMAIL_TYPE", "success")
APP_SECRETS_ARN = os.environ["APP_SECRETS_ARN"]

# ── Clients (module level — patched directly in tests) ───────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)
dynamodb = boto3.resource("dynamodb")
s3_client = boto3.client("s3")
secrets_client = boto3.client("secretsmanager")


@lru_cache(maxsize=1)
def get_secrets() -> dict:
    raw = secrets_client.get_secret_value(SecretId=APP_SECRETS_ARN)
    return json.loads(raw["SecretString"])


def _resolve_email_type(event: dict) -> str:
    """Failure if the event says so, else success. Robust to either the
    EventBridge detail-type or an explicit email_type in the detail."""
    detail_type = event.get("detail-type", "")
    detail = event.get("detail", {})
    if detail_type == "ScanFailed" or detail.get("email_type") == "failure":
        return "failure"
    if detail_type == "ReportGenerated" or detail.get("email_type") == "success":
        return "success"
    return EMAIL_TYPE_DEFAULT


def handler(event, context):
    detail = event.get("detail", {})
    scan_job_id = detail.get("scan_job_id")
    email_type = _resolve_email_type(event)

    logger.info(
        json.dumps(
            {"event": "email_start", "scan_job_id": scan_job_id, "email_type": email_type}
        )
    )

    if not scan_job_id:
        logger.error(json.dumps({"error": "missing_scan_job_id", "detail": detail}))
        return {"statusCode": 400}

    try:
        if email_type == "failure":
            _send_failure(scan_job_id)
        else:
            _send_success(scan_job_id)
        return {"statusCode": 200, "email_type": email_type}
    except Exception as exc:  # noqa: BLE001
        logger.error(
            json.dumps(
                {
                    "event": "email_failed",
                    "scan_job_id": scan_job_id,
                    "email_type": email_type,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
            )
        )
        raise


def _get_job(scan_job_id: str) -> dict | None:
    items = (
        dynamodb.Table(SCAN_JOBS_TABLE)
        .query(KeyConditionExpression=DdbKey("scan_job_id").eq(scan_job_id))
        .get("Items", [])
    )
    if not items:
        return None
    job = items[0]
    job.setdefault("scan_job_id", scan_job_id)
    return job


def _send_success(scan_job_id: str) -> None:
    secrets = get_secrets()
    from_addr = secrets["ses_from_email"]
    to_addr = secrets["ses_to_email"]

    job = _get_job(scan_job_id)
    if job is None:
        raise ValueError(f"scan_job_not_found: {scan_job_id}")

    findings = (
        dynamodb.Table(FINDINGS_TABLE)
        .query(KeyConditionExpression=DdbKey("scan_job_id").eq(scan_job_id))
        .get("Items", [])
    )

    report_key = job.get("report_s3_key", f"{scan_job_id}/report.pdf")
    pdf_bytes = s3_client.get_object(Bucket=REPORTS_BUCKET, Key=report_key)["Body"].read()

    msg = email_service.build_success_email(
        scan_job=job,
        findings=findings,
        pdf_bytes=pdf_bytes,
        cloudfront_url=CLOUDFRONT_URL,
        from_addr=from_addr,
        to_addr=to_addr,
    )
    email_service.send_email(msg, from_addr, to_addr)
    logger.info(json.dumps({"event": "success_email_sent", "scan_job_id": scan_job_id}))


def _send_failure(scan_job_id: str) -> None:
    secrets = get_secrets()
    from_addr = secrets["ses_from_email"]
    to_addr = secrets["ses_to_email"]

    job = _get_job(scan_job_id)
    if job is None:
        raise ValueError(f"scan_job_not_found: {scan_job_id}")

    msg = email_service.build_failure_email(
        scan_job=job, env=ENV, from_addr=from_addr, to_addr=to_addr
    )
    email_service.send_email(msg, from_addr, to_addr)
    logger.info(
        json.dumps(
            {
                "event": "failure_email_sent",
                "scan_job_id": scan_job_id,
                "failed_stage": job.get("failed_stage", "unknown"),
            }
        )
    )
