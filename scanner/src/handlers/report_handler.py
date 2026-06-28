"""Report Lambda — turns a completed AI analysis into a PDF in S3.

Triggered by the EventBridge AIAnalysisComplete event (custom guardrail bus,
published by the ai-analyzer). It:

  1. Reads the scan_job + all findings from DynamoDB.
  2. Renders the full PDF (all severities) via report_generator.pdf_generator.
  3. Uploads it to scan-reports/{scan_job_id}/report.pdf.
  4. Records report_s3_key on the scan-jobs row.
  5. Publishes ReportGenerated so the email-handler can send the report out.
"""
import json
import logging
import os

import boto3
from boto3.dynamodb.conditions import Key as DdbKey

from src.report_generator import pdf_generator

# ── Plain env vars — fail fast at module load ────────────────────────────────
SCAN_JOBS_TABLE = os.environ["SCAN_JOBS_TABLE"]
FINDINGS_TABLE = os.environ["FINDINGS_TABLE"]
REPORTS_BUCKET = os.environ["REPORTS_BUCKET"]
EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME", "default")

# ── Clients (module level — patched directly in tests) ───────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)
dynamodb = boto3.resource("dynamodb")
s3_client = boto3.client("s3")
events_client = boto3.client("events")


def handler(event, context):
    """EventBridge AIAnalysisComplete -> PDF report."""
    detail = event.get("detail", {})
    scan_job_id = detail.get("scan_job_id")

    logger.info(json.dumps({"event": "report_start", "scan_job_id": scan_job_id}))

    if not scan_job_id:
        logger.error(json.dumps({"error": "missing_scan_job_id", "detail": detail}))
        return {"statusCode": 400}

    try:
        report_key = _generate_report(scan_job_id)
        return {"statusCode": 200, "report_s3_key": report_key}
    except Exception as exc:  # noqa: BLE001 — log + re-raise so Lambda marks failure
        logger.error(
            json.dumps(
                {
                    "event": "report_failed",
                    "scan_job_id": scan_job_id,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
            )
        )
        raise


def _generate_report(scan_job_id: str) -> str:
    jobs_table = dynamodb.Table(SCAN_JOBS_TABLE)
    findings_table = dynamodb.Table(FINDINGS_TABLE)

    job_items = jobs_table.query(
        KeyConditionExpression=DdbKey("scan_job_id").eq(scan_job_id)
    ).get("Items", [])
    if not job_items:
        logger.error(json.dumps({"error": "scan_job_not_found", "scan_job_id": scan_job_id}))
        raise ValueError(f"scan_job_not_found: {scan_job_id}")
    job = job_items[0]
    # pdf_generator reads scan_job_id off the dict — ensure it's present.
    job.setdefault("scan_job_id", scan_job_id)

    findings = findings_table.query(
        KeyConditionExpression=DdbKey("scan_job_id").eq(scan_job_id)
    ).get("Items", [])

    pdf_bytes = pdf_generator.generate(job, findings)
    report_key = f"{scan_job_id}/report.pdf"

    s3_client.put_object(
        Bucket=REPORTS_BUCKET,
        Key=report_key,
        Body=pdf_bytes,
        ContentType="application/pdf",
    )

    jobs_table.update_item(
        Key={"scan_job_id": scan_job_id, "created_at": job["created_at"]},
        UpdateExpression="SET report_s3_key = :k, #s = :s",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":k": report_key, ":s": "REPORT_COMPLETE"},
    )

    events_client.put_events(
        Entries=[
            {
                "Source": "guardrail",
                "DetailType": "ReportGenerated",
                "EventBusName": EVENT_BUS_NAME,
                "Detail": json.dumps(
                    {"scan_job_id": scan_job_id, "report_s3_key": report_key}
                ),
            }
        ]
    )

    logger.info(
        json.dumps(
            {
                "event": "report_generated",
                "scan_job_id": scan_job_id,
                "report_s3_key": report_key,
                "pdf_bytes": len(pdf_bytes),
                "finding_count": len(findings),
            }
        )
    )
    return report_key
