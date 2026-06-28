"""/v1/scans routes — create (presigned upload), list, and detail.

Each route returns a (status_code, payload) tuple; the app dispatcher wraps it
with CORS headers and JSON-encodes it.
"""
import os
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

SCAN_JOBS_TABLE = os.environ["SCAN_JOBS_TABLE"]
FINDINGS_TABLE = os.environ["FINDINGS_TABLE"]
UPLOAD_BUCKET = os.environ["UPLOAD_BUCKET"]

UPLOAD_PRESIGN_EXPIRY = 300  # 5 minutes
LIST_LIMIT = 50
ALLOWED_EXTENSIONS = (".tf", ".hcl", ".yaml", ".yml", ".json", ".template")

# Module-level clients — created once per cold start, intercepted by moto in tests.
dynamodb = boto3.resource("dynamodb")
s3_client = boto3.client("s3")


def _iac_type(file_name: str) -> str:
    return "terraform" if file_name.endswith((".tf", ".hcl")) else "cloudformation"


def create_scan(claims: dict, body: dict) -> tuple[int, dict]:
    """Mint a scan_job_id, return a presigned PUT URL, and create the QUEUED record.

    The scan_job_id is embedded in the S3 key (uploads/<id>/<file>) so the
    S3-triggered ingest handler reuses THIS record instead of creating a second
    one — one job, one row, end to end.
    """
    file_name = (body or {}).get("file_name")
    if not file_name or not file_name.endswith(ALLOWED_EXTENSIONS):
        return 400, {"error": "file_name with a supported IaC extension is required"}

    scan_job_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    s3_key = f"uploads/{scan_job_id}/{file_name}"

    presigned_url = s3_client.generate_presigned_url(
        "put_object",
        Params={"Bucket": UPLOAD_BUCKET, "Key": s3_key},
        ExpiresIn=UPLOAD_PRESIGN_EXPIRY,
    )

    dynamodb.Table(SCAN_JOBS_TABLE).put_item(
        Item={
            "scan_job_id": scan_job_id,
            "created_at": created_at,
            "status": "QUEUED",
            "file_name": file_name,
            "s3_key": s3_key,
            "s3_bucket": UPLOAD_BUCKET,
            "iac_type": _iac_type(file_name),
            "risk_score": 0,
            "finding_counts": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
            "created_by": claims.get("sub", "unknown"),
        }
    )
    return 200, {
        "scan_job_id": scan_job_id,
        "presigned_url": presigned_url,
        "status": "QUEUED",
    }


def list_scans(claims: dict, query: dict) -> tuple[int, list]:
    """Return up to 50 scans, newest first (summary fields only)."""
    items = dynamodb.Table(SCAN_JOBS_TABLE).scan().get("Items", [])
    items.sort(key=lambda i: i.get("created_at", ""), reverse=True)
    summary = [
        {
            "scan_job_id": i.get("scan_job_id"),
            "file_name": i.get("file_name"),
            "status": i.get("status"),
            "risk_score": i.get("risk_score", 0),
            "finding_counts": i.get("finding_counts", {}),
            "created_at": i.get("created_at"),
        }
        for i in items[:LIST_LIMIT]
    ]
    return 200, summary


def get_scan(claims: dict, scan_job_id: str) -> tuple[int, dict]:
    """Return full scan detail plus all findings (with AI explanation/fix)."""
    jobs = (
        dynamodb.Table(SCAN_JOBS_TABLE)
        .query(KeyConditionExpression=Key("scan_job_id").eq(scan_job_id))
        .get("Items", [])
    )
    if not jobs:
        return 404, {"error": "scan not found"}

    findings = (
        dynamodb.Table(FINDINGS_TABLE)
        .query(KeyConditionExpression=Key("scan_job_id").eq(scan_job_id))
        .get("Items", [])
    )
    job = jobs[0]
    job["findings"] = findings
    return 200, job
