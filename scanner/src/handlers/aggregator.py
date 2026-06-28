import json
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key as DdbKey

# Module-level env vars — fail fast if missing
SCAN_JOBS_TABLE = os.environ["SCAN_JOBS_TABLE"]
FINDINGS_TABLE = os.environ["FINDINGS_TABLE"]
EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME", "default")

# Module-level clients
logger = logging.getLogger()
logger.setLevel(logging.INFO)
dynamodb = boto3.resource("dynamodb")
events_client = boto3.client("events")


def handler(event, context):
    """
    Lambda handler triggered by SQS guardrail-checkov-results queue.
    Processes Fargate Checkov findings, deduplicates, writes to DDB, updates scan status.
    """
    logger.info(json.dumps({"event": "aggregator_start", "record_count": len(event.get("Records", []))}))

    try:
        for record in event.get("Records", []):
            body_str = record.get("body", "{}")
            msg = json.loads(body_str)
            scan_job_id = msg.get("scan_job_id")
            findings = msg.get("findings", [])

            if not scan_job_id:
                logger.warning(json.dumps({"warning": "missing_scan_job_id", "message": msg}))
                continue

            _process_findings(scan_job_id, findings)

        return {"statusCode": 200}

    except Exception as e:
        logger.error(json.dumps({"error": "handler_failed", "exception": str(e)}))
        raise


def _process_findings(scan_job_id: str, findings: list) -> None:
    """
    1. Load existing findings for this scan_job_id
    2. Deduplicate by rule_id + resource_name
    3. Write new findings to DDB
    4. Update scan-jobs status to COMPLETE and set finding_counts
    5. Publish EventBridge ScanComplete event
    """
    findings_table = dynamodb.Table(FINDINGS_TABLE)
    jobs_table = dynamodb.Table(SCAN_JOBS_TABLE)

    logger.info(json.dumps({
        "event": "process_findings_start",
        "scan_job_id": scan_job_id,
        "new_findings_count": len(findings),
    }))

    # Step 1: Load existing findings to deduplicate
    existing_response = findings_table.query(
        KeyConditionExpression=DdbKey("scan_job_id").eq(scan_job_id)
    )
    existing_items = existing_response.get("Items", [])
    existing_keys = {(item["rule_id"], item["resource_name"]) for item in existing_items}

    logger.info(json.dumps({
        "event": "existing_findings_loaded",
        "scan_job_id": scan_job_id,
        "existing_count": len(existing_items),
    }))

    # Step 2: Filter for new findings only
    new_findings = [
        f for f in findings
        if (f.get("rule_id"), f.get("resource_name")) not in existing_keys
    ]

    logger.info(json.dumps({
        "event": "findings_deduplicated",
        "scan_job_id": scan_job_id,
        "new_findings_to_write": len(new_findings),
    }))

    # Step 3: Write new findings to DDB using batch_writer
    if new_findings:
        with findings_table.batch_writer() as batch:
            for f in new_findings:
                batch.put_item(
                    Item={
                        "scan_job_id": scan_job_id,
                        "finding_id": str(uuid.uuid4()),
                        "rule_id": f.get("rule_id", ""),
                        "severity": f.get("severity", "LOW"),
                        "resource_name": f.get("resource_name", ""),
                        "resource_type": f.get("resource_type", ""),
                        "line_number": Decimal(str(f.get("line_number", 0))),
                        "code_snippet": f.get("code_snippet", "")[:500],
                        "ai_explanation": "",
                        "ai_fix_code": "",
                        "dismissed": False,
                        "source": "checkov",
                    }
                )

        logger.info(json.dumps({
            "event": "findings_written",
            "scan_job_id": scan_job_id,
            "written_count": len(new_findings),
        }))

    # Step 4: Query ALL findings for this scan to count by severity
    all_findings_response = findings_table.query(
        KeyConditionExpression=DdbKey("scan_job_id").eq(scan_job_id)
    )
    all_findings = all_findings_response.get("Items", [])

    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for item in all_findings:
        severity = item.get("severity", "LOW")
        counts[severity] = counts.get(severity, 0) + 1

    logger.info(json.dumps({
        "event": "findings_counted",
        "scan_job_id": scan_job_id,
        "counts": counts,
    }))

    # Step 5: Update scan-jobs status to COMPLETE
    job_response = jobs_table.query(
        KeyConditionExpression=DdbKey("scan_job_id").eq(scan_job_id)
    )
    if not job_response.get("Items"):
        logger.error(json.dumps({
            "error": "scan_job_not_found",
            "scan_job_id": scan_job_id,
        }))
        return

    job = job_response["Items"][0]
    created_at = job["created_at"]

    jobs_table.update_item(
        Key={"scan_job_id": scan_job_id, "created_at": created_at},
        UpdateExpression="SET #s = :s, finding_counts = :fc, updated_at = :t",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":s": "COMPLETE",
            ":fc": {k: Decimal(str(v)) for k, v in counts.items()},
            ":t": datetime.now(timezone.utc).isoformat(),
        },
    )

    logger.info(json.dumps({
        "event": "scan_job_updated_to_complete",
        "scan_job_id": scan_job_id,
    }))

    # Step 6: Publish EventBridge ScanComplete event
    total = sum(counts.values())
    raw_score = (
        counts["CRITICAL"] * 40
        + counts["HIGH"] * 20
        + counts["MEDIUM"] * 5
        + counts["LOW"] * 1
    )
    risk_score = int(min(raw_score, 200) / 200 * 100)

    events_client.put_events(
        Entries=[
            {
                "Source": "guardrail",
                "DetailType": "ScanComplete",
                "Detail": json.dumps({
                    "scan_job_id": scan_job_id,
                    "risk_score_raw": raw_score,
                    "risk_score": risk_score,
                    "finding_counts": {k: int(v) for k, v in counts.items()},
                }),
                "EventBusName": EVENT_BUS_NAME,
            }
        ]
    )

    logger.info(json.dumps({
        "event": "scan_complete_published",
        "scan_job_id": scan_job_id,
        "risk_score": risk_score,
        "finding_counts": counts,
    }))
