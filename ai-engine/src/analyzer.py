"""AI analysis Lambda — explains every finding and generates fixes for the worst.

Triggered by the EventBridge ScanComplete event (published by the aggregator on
the custom guardrail bus). For each finding of the scan it:

  1. Calls Bedrock (Haiku) to produce a plain-English ai_explanation.
  2. For CRITICAL/HIGH findings only, calls Bedrock (Sonnet) to produce ai_fix_code
     (cost guard — MEDIUM/LOW never trigger the more expensive fix model).
  3. Writes both back to the findings table.

Then it computes a deterministic risk_score (0-100) from severities, flips the
scan-job to AI_COMPLETE, and publishes AIAnalysisComplete for the report stage.
"""
import json
import logging
import os
from decimal import Decimal
from pathlib import Path

import boto3
from boto3.dynamodb.conditions import Key as DdbKey

from src.bedrock_client import BedrockClient

# ── Plain env vars — fail fast at module load ────────────────────────────────
FINDINGS_TABLE = os.environ["FINDINGS_TABLE"]
SCAN_JOBS_TABLE = os.environ["SCAN_JOBS_TABLE"]
EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME", "default")

# ── Clients (module level — patched directly in tests) ───────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)
dynamodb = boto3.resource("dynamodb")
events_client = boto3.client("events")
bedrock = BedrockClient()

# ── Risk score contract (mirrors score_risk.txt / CLAUDE.md) ─────────────────
WEIGHTS = {"CRITICAL": 40, "HIGH": 20, "MEDIUM": 5, "LOW": 1}
MAX_POSSIBLE = 200
FIX_SEVERITIES = ("CRITICAL", "HIGH")

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def handler(event, context):
    """Lambda entry point — EventBridge ScanComplete -> AI analysis."""
    detail = event.get("detail", {})
    scan_job_id = detail.get("scan_job_id")

    logger.info(json.dumps({"event": "ai_analysis_start", "scan_job_id": scan_job_id}))

    if not scan_job_id:
        logger.error(json.dumps({"error": "missing_scan_job_id", "detail": detail}))
        return {"statusCode": 400}

    try:
        risk_score = _run_analysis(scan_job_id)
        return {"statusCode": 200, "risk_score": risk_score}
    except Exception as exc:  # noqa: BLE001 — log + re-raise so Lambda marks failure
        logger.error(
            json.dumps(
                {
                    "event": "ai_analysis_failed",
                    "scan_job_id": scan_job_id,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
            )
        )
        raise


def _run_analysis(scan_job_id: str) -> int:
    findings_table = dynamodb.Table(FINDINGS_TABLE)
    jobs_table = dynamodb.Table(SCAN_JOBS_TABLE)

    job = _get_job(jobs_table, scan_job_id)
    if job is None:
        logger.error(json.dumps({"error": "scan_job_not_found", "scan_job_id": scan_job_id}))
        return 0
    iac_type = job.get("iac_type") or job.get("file_type") or "terraform"

    findings = findings_table.query(
        KeyConditionExpression=DdbKey("scan_job_id").eq(scan_job_id)
    ).get("Items", [])

    logger.info(
        json.dumps(
            {
                "event": "findings_loaded",
                "scan_job_id": scan_job_id,
                "finding_count": len(findings),
            }
        )
    )

    explain_tpl = _load_prompt("explain_risk.txt")
    fix_tpl = _load_prompt("generate_fix.txt")

    for finding in findings:
        severity = finding.get("severity", "LOW")

        explanation = bedrock.explain_risk(
            _render(
                explain_tpl,
                {
                    "rule_id": finding.get("rule_id", ""),
                    "resource_name": finding.get("resource_name", ""),
                    "resource_type": finding.get("resource_type", ""),
                    "code_snippet": finding.get("code_snippet", ""),
                },
            )
        )

        fix_code = ""
        if severity in FIX_SEVERITIES:
            fix_code = bedrock.generate_fix(
                _render(
                    fix_tpl,
                    {
                        "iac_type": iac_type,
                        "rule_id": finding.get("rule_id", ""),
                        "resource_name": finding.get("resource_name", ""),
                        "resource_type": finding.get("resource_type", ""),
                        "code_snippet": finding.get("code_snippet", ""),
                    },
                )
            )

        findings_table.update_item(
            Key={"scan_job_id": scan_job_id, "finding_id": finding["finding_id"]},
            UpdateExpression="SET ai_explanation = :e, ai_fix_code = :f",
            ExpressionAttributeValues={":e": explanation, ":f": fix_code},
        )

    risk_score = _calculate_risk_score(findings)

    jobs_table.update_item(
        Key={"scan_job_id": scan_job_id, "created_at": job["created_at"]},
        UpdateExpression="SET #s = :s, risk_score = :r",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": "AI_COMPLETE", ":r": Decimal(str(risk_score))},
    )

    events_client.put_events(
        Entries=[
            {
                "Source": "guardrail",
                "DetailType": "AIAnalysisComplete",
                "EventBusName": EVENT_BUS_NAME,
                "Detail": json.dumps(
                    {"scan_job_id": scan_job_id, "risk_score": risk_score}
                ),
            }
        ]
    )

    logger.info(
        json.dumps(
            {
                "event": "ai_analysis_complete",
                "scan_job_id": scan_job_id,
                "risk_score": risk_score,
                "finding_count": len(findings),
            }
        )
    )
    return risk_score


def _calculate_risk_score(findings: list) -> int:
    """Sum severity weights, cap at 200, normalize to 0-100."""
    raw = sum(WEIGHTS.get(f.get("severity", "LOW"), 0) for f in findings)
    normalized = min(raw, MAX_POSSIBLE)
    return int(normalized / MAX_POSSIBLE * 100)


def _get_job(jobs_table, scan_job_id: str):
    items = jobs_table.query(
        KeyConditionExpression=DdbKey("scan_job_id").eq(scan_job_id)
    ).get("Items", [])
    return items[0] if items else None


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8")


def _render(template: str, values: dict) -> str:
    """Substitute {key} placeholders. Uses replace (not str.format) so literal
    braces in code snippets — e.g. IAM policy JSON — never break rendering."""
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", str(value))
    return rendered
