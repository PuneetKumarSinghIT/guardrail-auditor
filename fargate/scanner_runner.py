import os
import json
import subprocess
import tempfile
import logging
import pathlib
import boto3
import uuid

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SCAN_JOB_ID = os.environ["SCAN_JOB_ID"]
S3_BUCKET = os.environ["S3_BUCKET"]
S3_KEY = os.environ["S3_KEY"]
SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]

CHECKOV_TO_RULE = {
    "CKV_AWS_20": "S3-001",
    "CKV_AWS_93": "S3-002",
    "CKV_AWS_21": "S3-003",
    "CKV_AWS_19": "S3-004",
    "CKV_AWS_18": "S3-005",
    "CKV_AWS_25": "SG-001",
    "CKV_AWS_24": "SG-002",
    "CKV_AWS_23": "SG-003",
    "CKV_AWS_260": "IAM-001",
    "CKV_AWS_49": "IAM-002",
    "CKV_AWS_7": "ENC-001",
    "CKV_AWS_17": "ENC-002",
    "CKV_AWS_36": "LOG-001",
    "CKV_AWS_73": "LOG-002",
}

SEVERITY_MAP = {
    "S3-001": "CRITICAL",
    "S3-002": "CRITICAL",
    "S3-003": "MEDIUM",
    "S3-004": "HIGH",
    "S3-005": "LOW",
    "SG-001": "CRITICAL",
    "SG-002": "CRITICAL",
    "SG-003": "CRITICAL",
    "SG-004": "MEDIUM",
    "IAM-001": "HIGH",
    "IAM-002": "HIGH",
    "IAM-003": "CRITICAL",
    "IAM-004": "HIGH",
    "IAM-005": "LOW",
    "ENC-001": "HIGH",
    "ENC-002": "HIGH",
    "ENC-003": "CRITICAL",
    "LOG-001": "HIGH",
    "LOG-002": "MEDIUM",
    "LOG-003": "LOW",
}


def download_iac_file(s3_client, bucket, key):
    """Download IaC file from S3 to temporary location."""
    ext = pathlib.Path(key).suffix or ".tf"
    temp_file = f"/tmp/iac_file{ext}"
    try:
        s3_client.download_file(bucket, key, temp_file)
        logger.info(json.dumps({"event": "file_downloaded", "bucket": bucket, "key": key, "local_path": temp_file}))
        return temp_file
    except Exception as e:
        logger.error(json.dumps({"event": "download_failed", "error": str(e), "bucket": bucket, "key": key}))
        raise


def run_checkov(file_path):
    """Run checkov and return parsed JSON output."""
    cmd = ["checkov", "-f", file_path, "--output", "json", "--quiet", "--compact"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.warning(json.dumps({
                "event": "checkov_non_zero_exit",
                "exit_code": result.returncode,
                "stderr": result.stderr[:500]
            }))
        if not result.stdout:
            logger.warning(json.dumps({"event": "checkov_empty_output", "file": file_path}))
            return {"results": {"failed_checks": []}}
        try:
            output = json.loads(result.stdout)
            logger.info(json.dumps({"event": "checkov_completed", "file": file_path}))
            return output
        except json.JSONDecodeError as e:
            logger.error(json.dumps({"event": "checkov_json_parse_failed", "error": str(e)}))
            return {"results": {"failed_checks": []}}
    except Exception as e:
        logger.error(json.dumps({"event": "checkov_execution_failed", "error": str(e)}))
        raise


def map_findings(checkov_output, scan_job_id):
    """Convert checkov failed_checks to Finding dicts."""
    findings = []
    failed_checks = checkov_output.get("results", {}).get("failed_checks", [])

    for check in failed_checks:
        check_id = check.get("check_id", "UNKNOWN")
        rule_id = CHECKOV_TO_RULE.get(check_id, check_id)
        severity = SEVERITY_MAP.get(rule_id, "MEDIUM")
        resource_name = check.get("resource", "unknown")
        resource_type = resource_name.split(".")[0] if "." in resource_name else "resource"
        line_number = check.get("file_line_range", [0])[0]
        code_block = check.get("code_block", [[]])
        code_snippet = code_block[0][1] if code_block and len(code_block[0]) > 1 else ""
        code_snippet = code_snippet[:500]

        finding = {
            "rule_id": rule_id,
            "severity": severity,
            "resource_name": resource_name,
            "resource_type": resource_type,
            "line_number": line_number,
            "code_snippet": code_snippet,
        }
        findings.append(finding)

    logger.info(json.dumps({"event": "findings_mapped", "count": len(findings)}))
    return findings


def send_to_sqs(sqs_client, queue_url, scan_job_id, findings_batch):
    """Send findings batch to SQS queue."""
    message_body = {
        "scan_job_id": scan_job_id,
        "source": "checkov",
        "findings": findings_batch,
    }
    try:
        sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body),
        )
        logger.info(json.dumps({
            "event": "sqs_message_sent",
            "scan_job_id": scan_job_id,
            "findings_count": len(findings_batch),
        }))
    except Exception as e:
        logger.error(json.dumps({"event": "sqs_send_failed", "error": str(e)}))
        raise


def main():
    """Main execution flow."""
    logger.info(json.dumps({
        "event": "scanner_started",
        "scan_job_id": SCAN_JOB_ID,
        "s3_bucket": S3_BUCKET,
        "s3_key": S3_KEY,
    }))

    s3_client = boto3.client("s3")
    sqs_client = boto3.client("sqs")

    file_path = download_iac_file(s3_client, S3_BUCKET, S3_KEY)
    checkov_output = run_checkov(file_path)
    findings = map_findings(checkov_output, SCAN_JOB_ID)

    batch_size = 10
    for i in range(0, len(findings), batch_size):
        batch = findings[i:i + batch_size]
        send_to_sqs(sqs_client, SQS_QUEUE_URL, SCAN_JOB_ID, batch)

    if not findings:
        send_to_sqs(sqs_client, SQS_QUEUE_URL, SCAN_JOB_ID, [])

    logger.info(json.dumps({
        "event": "scanner_completed",
        "scan_job_id": SCAN_JOB_ID,
        "total_findings": len(findings),
    }))


if __name__ == "__main__":
    main()
