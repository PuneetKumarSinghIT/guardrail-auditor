"""Failure Lambda — marks a scan FAILED and fans out a ScanFailed event.

Triggered by either of two sources:
  a) EventBridge: an ECS Task State Change where a container exited non-zero
     (a rules-engine or checkov Fargate task crashed mid-scan).
  b) SNS: the checkov-results DLQ depth alarm fired (poison messages piled up).

Both converge here. The handler identifies the scan_job_id and the failed
stage, flips scan-jobs to FAILED with debug context, and publishes ScanFailed
so the email-handler sends the developer-attention email.
"""
import json
import logging
import os
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key as DdbKey

SCAN_JOBS_TABLE = os.environ["SCAN_JOBS_TABLE"]
EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME", "default")

logger = logging.getLogger()
logger.setLevel(logging.INFO)
dynamodb = boto3.resource("dynamodb")
events_client = boto3.client("events")


def handler(event, context):
    logger.info(json.dumps({"event": "failure_handler_start"}))
    try:
        info = _extract(event)
        if not info or not info.get("scan_job_id"):
            logger.warning(json.dumps({"warning": "no_scan_job_id_in_event", "event": _safe(event)}))
            return {"statusCode": 200, "skipped": True}

        _mark_failed(info)
        _publish_scan_failed(info)
        return {"statusCode": 200, "scan_job_id": info["scan_job_id"]}
    except Exception as exc:  # noqa: BLE001
        logger.error(
            json.dumps(
                {"event": "failure_handler_error", "error": str(exc), "error_type": type(exc).__name__}
            )
        )
        raise


def _extract(event: dict) -> dict:
    """Normalise either trigger shape into {scan_job_id, failed_stage, error_message, trace_id}."""
    # SNS-wrapped DLQ alarm
    if "Records" in event and event["Records"] and "Sns" in event["Records"][0]:
        sns = event["Records"][0]["Sns"]
        message = sns.get("Message", "")
        scan_job_id = None
        try:
            parsed = json.loads(message)
            scan_job_id = parsed.get("scan_job_id")
        except (ValueError, TypeError):
            pass
        return {
            "scan_job_id": scan_job_id,
            "failed_stage": "checkov",
            "error_message": "Checkov results landed in the dead-letter queue (DLQ depth alarm).",
            "trace_id": "",
        }

    # EventBridge ECS Task State Change
    detail = event.get("detail", {})
    containers = detail.get("containers", [])
    failed = next(
        (c for c in containers if c.get("exitCode") not in (0, None)),
        containers[0] if containers else {},
    )
    failed_stage = _stage_from(detail, failed)
    scan_job_id = _scan_job_id_from_overrides(detail)
    exit_code = failed.get("exitCode")
    reason = failed.get("reason") or detail.get("stoppedReason") or "ECS task exited non-zero"
    return {
        "scan_job_id": scan_job_id,
        "failed_stage": failed_stage,
        "error_message": f"{reason} (exitCode={exit_code})",
        "trace_id": detail.get("traceId", ""),
    }


def _stage_from(detail: dict, container: dict) -> str:
    name = container.get("name", "")
    if name:
        return name
    # Fall back to the task-definition family (…/guardrail-rules-engine-dev:3)
    arn = detail.get("taskDefinitionArn", "")
    if "rules-engine" in arn:
        return "rules-engine"
    if "checkov" in arn:
        return "checkov"
    return "unknown"


def _scan_job_id_from_overrides(detail: dict) -> str | None:
    overrides = detail.get("overrides", {}).get("containerOverrides", [])
    for co in overrides:
        for env_var in co.get("environment", []):
            if env_var.get("name") == "SCAN_JOB_ID":
                return env_var.get("value")
    return None


def _mark_failed(info: dict) -> None:
    table = dynamodb.Table(SCAN_JOBS_TABLE)
    items = table.query(
        KeyConditionExpression=DdbKey("scan_job_id").eq(info["scan_job_id"])
    ).get("Items", [])
    if not items:
        logger.warning(json.dumps({"warning": "scan_job_not_found", "scan_job_id": info["scan_job_id"]}))
        return
    created_at = items[0]["created_at"]
    table.update_item(
        Key={"scan_job_id": info["scan_job_id"], "created_at": created_at},
        UpdateExpression=(
            "SET #s = :s, failed_stage = :fs, error_message = :em, "
            "trace_id = :t, updated_at = :u"
        ),
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":s": "FAILED",
            ":fs": info.get("failed_stage", "unknown"),
            ":em": info.get("error_message", ""),
            ":t": info.get("trace_id", ""),
            ":u": datetime.now(timezone.utc).isoformat(),
        },
    )
    logger.info(json.dumps({"event": "scan_marked_failed", "scan_job_id": info["scan_job_id"]}))


def _publish_scan_failed(info: dict) -> None:
    events_client.put_events(
        Entries=[
            {
                "Source": "guardrail",
                "DetailType": "ScanFailed",
                "EventBusName": EVENT_BUS_NAME,
                "Detail": json.dumps(
                    {
                        "scan_job_id": info["scan_job_id"],
                        "failed_stage": info.get("failed_stage", "unknown"),
                        "error_message": info.get("error_message", ""),
                        "trace_id": info.get("trace_id", ""),
                    }
                ),
            }
        ]
    )
    logger.info(json.dumps({"event": "scan_failed_published", "scan_job_id": info["scan_job_id"]}))


def _safe(event: dict) -> str:
    try:
        return json.dumps(event)[:500]
    except (TypeError, ValueError):
        return str(event)[:500]
