"""/v1/scans/{id}/report route — presigned URL to the generated PDF report."""
import os

import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config

SCAN_JOBS_TABLE = os.environ["SCAN_JOBS_TABLE"]
REPORTS_BUCKET = os.environ["REPORTS_BUCKET"]

REPORT_PRESIGN_EXPIRY = 900  # 15 minutes

dynamodb = boto3.resource("dynamodb")
# SigV4 is REQUIRED for presigned URLs against an SSE-KMS bucket — the default
# SigV2 presign is rejected by S3 with "Requests specifying Server Side
# Encryption with AWS KMS managed keys require AWS Signature Version 4" (HTTP 400).
# The scan-reports bucket is KMS-encrypted, so force s3v4 here.
s3_client = boto3.client("s3", config=Config(signature_version="s3v4"))


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

    # Force a browser DOWNLOAD (not inline render) with a friendly filename. The
    # dashboard is a different origin from S3, so the anchor `download` attribute is
    # ignored — this response header is what actually names + downloads the file.
    file_name = jobs[0].get("file_name", "scan")
    download_name = f"{file_name}-guardrail-report.pdf"
    url = s3_client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": REPORTS_BUCKET,
            "Key": report_key,
            "ResponseContentType": "application/pdf",
            "ResponseContentDisposition": f'attachment; filename="{download_name}"',
        },
        ExpiresIn=REPORT_PRESIGN_EXPIRY,
    )
    return 200, {"report_url": url, "expires_in": REPORT_PRESIGN_EXPIRY}
