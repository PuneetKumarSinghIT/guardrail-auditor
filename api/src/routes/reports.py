"""/v1/scans/{id}/report route — presigned URL to the generated PDF report."""
import os

import boto3
from boto3.dynamodb.conditions import Key

SCAN_JOBS_TABLE = os.environ["SCAN_JOBS_TABLE"]
REPORTS_BUCKET = os.environ["REPORTS_BUCKET"]

REPORT_PRESIGN_EXPIRY = 900  # 15 minutes

dynamodb = boto3.resource("dynamodb")
s3_client = boto3.client("s3")


def get_report_url(claims: dict, scan_job_id: str) -> tuple[int, dict]:
    """Return a 15-minute presigned GET URL for the scan's PDF report.

    404 if the scan does not exist or the report has not been generated yet
    (report_s3_key is written by the report-handler in Phase 9).
    """
    jobs = (
        dynamodb.Table(SCAN_JOBS_TABLE)
        .query(KeyConditionExpression=Key("scan_job_id").eq(scan_job_id))
        .get("Items", [])
    )
    if not jobs:
        return 404, {"error": "scan not found"}

    report_key = jobs[0].get("report_s3_key")
    if not report_key:
        return 404, {"error": "report not yet generated"}

    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": REPORTS_BUCKET, "Key": report_key},
        ExpiresIn=REPORT_PRESIGN_EXPIRY,
    )
    return 200, {"report_url": url, "expires_in": REPORT_PRESIGN_EXPIRY}
