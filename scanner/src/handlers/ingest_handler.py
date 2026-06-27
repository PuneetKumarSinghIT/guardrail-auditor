import json
import logging
import os
import uuid
from datetime import datetime, timezone

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SCAN_JOBS_TABLE = os.environ["SCAN_JOBS_TABLE"]
EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME", "default")

dynamodb = boto3.resource("dynamodb")
events_client = boto3.client("events")

ALLOWED_EXTENSIONS = {
    ".tf": "terraform",
    ".hcl": "terraform",
    ".yaml": "cloudformation",
    ".yml": "cloudformation",
    ".json": "cloudformation",
    ".template": "cloudformation",
}


def _detect_iac_type(key: str) -> str | None:
    for ext, iac_type in ALLOWED_EXTENSIONS.items():
        if key.endswith(ext):
            return iac_type
    return None


def _success(body: dict) -> dict:
    return {"statusCode": 200, "body": json.dumps(body)}


def _error(status: int, message: str) -> dict:
    return {"statusCode": status, "body": json.dumps({"error": message})}


def handler(event: dict, context) -> dict:
    logger.info(json.dumps({"event": "ingest_handler_invoked", "record_count": len(event.get("detail", {}))}))

    # EventBridge wraps the S3 event in a detail field
    detail = event.get("detail", event)
    bucket = detail.get("bucket", {}).get("name") or detail.get("s3", {}).get("bucket", {}).get("name")
    key = detail.get("object", {}).get("key") or detail.get("s3", {}).get("object", {}).get("key")

    if not bucket or not key:
        logger.error(json.dumps({"event": "missing_s3_fields", "detail": detail}))
        return _error(400, "Missing bucket or key in event")

    iac_type = _detect_iac_type(key)
    if not iac_type:
        logger.warning(json.dumps({"event": "invalid_extension_rejected", "key": key}))
        return _error(400, f"Unsupported file type for key: {key}")

    scan_job_id = str(uuid.uuid4())
    file_name = key.split("/")[-1]
    created_at = datetime.now(timezone.utc).isoformat()

    table = dynamodb.Table(SCAN_JOBS_TABLE)
    table.put_item(
        Item={
            "scan_job_id": scan_job_id,
            "created_at": created_at,
            "status": "QUEUED",
            "file_name": file_name,
            "s3_key": key,
            "s3_bucket": bucket,
            "iac_type": iac_type,
            "risk_score": 0,
            "finding_counts": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
        }
    )

    events_client.put_events(
        Entries=[
            {
                "Source": "guardrail",
                "DetailType": "ScanRequested",
                "Detail": json.dumps({
                    "scan_job_id": scan_job_id,
                    "s3_key": key,
                    "s3_bucket": bucket,
                    "iac_type": iac_type,
                }),
                "EventBusName": EVENT_BUS_NAME,
            }
        ]
    )

    logger.info(json.dumps({
        "event": "scan_job_created",
        "scan_job_id": scan_job_id,
        "file_name": file_name,
        "iac_type": iac_type,
    }))
    return _success({"scan_job_id": scan_job_id, "status": "QUEUED"})
