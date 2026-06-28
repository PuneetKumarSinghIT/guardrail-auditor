import os
from decimal import Decimal
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("FINDINGS_TABLE", "findings-test")
os.environ.setdefault("SCAN_JOBS_TABLE", "scan-jobs-test")
os.environ.setdefault("EVENT_BUS_NAME", "default")

from src import analyzer


def _setup_tables(ddb):
    scan_jobs = ddb.create_table(
        TableName="scan-jobs-test",
        KeySchema=[
            {"AttributeName": "scan_job_id", "KeyType": "HASH"},
            {"AttributeName": "created_at", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "scan_job_id", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    findings = ddb.create_table(
        TableName="findings-test",
        KeySchema=[
            {"AttributeName": "scan_job_id", "KeyType": "HASH"},
            {"AttributeName": "finding_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "scan_job_id", "AttributeType": "S"},
            {"AttributeName": "finding_id", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    return scan_jobs, findings


def _seed_job(scan_jobs, scan_job_id, iac_type="terraform"):
    scan_jobs.put_item(
        Item={
            "scan_job_id": scan_job_id,
            "created_at": "2026-01-01T00:00:00+00:00",
            "status": "COMPLETE",
            "iac_type": iac_type,
        }
    )


def _seed_finding(findings, scan_job_id, finding_id, severity, rule_id="S3-001"):
    findings.put_item(
        Item={
            "scan_job_id": scan_job_id,
            "finding_id": finding_id,
            "rule_id": rule_id,
            "severity": severity,
            "resource_name": "aws_s3_bucket.bad",
            "resource_type": "aws_s3_bucket",
            "line_number": Decimal("1"),
            "code_snippet": 'acl = "public-read"',
            "ai_explanation": "",
            "ai_fix_code": "",
        }
    )


def _event(scan_job_id):
    return {"detail": {"scan_job_id": scan_job_id, "risk_score": 0}}


@mock_aws
def test_all_findings_get_explanation():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    scan_jobs, findings = _setup_tables(ddb)
    _seed_job(scan_jobs, "job-1")
    _seed_finding(findings, "job-1", "f1", "CRITICAL")
    _seed_finding(findings, "job-1", "f2", "LOW", rule_id="S3-005")

    with patch.object(analyzer.bedrock, "explain_risk", return_value="It is dangerous."), \
         patch.object(analyzer.bedrock, "generate_fix", return_value="fixed code"):
        result = analyzer.handler(_event("job-1"), None)

    assert result["statusCode"] == 200
    items = findings.scan()["Items"]
    assert all(i["ai_explanation"] == "It is dangerous." for i in items)


@mock_aws
def test_critical_and_high_get_fix_code():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    scan_jobs, findings = _setup_tables(ddb)
    _seed_job(scan_jobs, "job-2")
    _seed_finding(findings, "job-2", "f1", "CRITICAL")

    with patch.object(analyzer.bedrock, "explain_risk", return_value="why"), \
         patch.object(analyzer.bedrock, "generate_fix", return_value="resource fixed {}"):
        analyzer.handler(_event("job-2"), None)

    item = findings.scan()["Items"][0]
    assert item["ai_fix_code"] == "resource fixed {}"


@mock_aws
def test_medium_low_skip_fix_generation_cost_guard():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    scan_jobs, findings = _setup_tables(ddb)
    _seed_job(scan_jobs, "job-3")
    _seed_finding(findings, "job-3", "f1", "MEDIUM", rule_id="S3-003")
    _seed_finding(findings, "job-3", "f2", "LOW", rule_id="S3-005")

    fix_mock = MagicMock(return_value="should not be called")
    with patch.object(analyzer.bedrock, "explain_risk", return_value="why"), \
         patch.object(analyzer.bedrock, "generate_fix", fix_mock):
        analyzer.handler(_event("job-3"), None)

    # cost guard: the expensive Sonnet fix model is never invoked for MEDIUM/LOW
    fix_mock.assert_not_called()
    for item in findings.scan()["Items"]:
        assert item["ai_fix_code"] == ""


@mock_aws
def test_risk_score_calculation_and_status_update():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    scan_jobs, findings = _setup_tables(ddb)
    _seed_job(scan_jobs, "job-4")
    # 1 CRITICAL (40) + 1 HIGH (20) = 60 raw -> 60/200*100 = 30
    _seed_finding(findings, "job-4", "f1", "CRITICAL")
    _seed_finding(findings, "job-4", "f2", "HIGH", rule_id="ENC-001")

    with patch.object(analyzer.bedrock, "explain_risk", return_value="why"), \
         patch.object(analyzer.bedrock, "generate_fix", return_value="fix"):
        result = analyzer.handler(_event("job-4"), None)

    assert result["risk_score"] == 30
    job = scan_jobs.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("scan_job_id").eq("job-4")
    )["Items"][0]
    assert job["status"] == "AI_COMPLETE"
    assert job["risk_score"] == Decimal("30")


@mock_aws
def test_ai_analysis_complete_event_published():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    scan_jobs, findings = _setup_tables(ddb)
    _seed_job(scan_jobs, "job-5")
    _seed_finding(findings, "job-5", "f1", "HIGH", rule_id="ENC-001")

    with patch.object(analyzer.bedrock, "explain_risk", return_value="why"), \
         patch.object(analyzer.bedrock, "generate_fix", return_value="fix"), \
         patch.object(analyzer.events_client, "put_events") as put_events:
        analyzer.handler(_event("job-5"), None)

    put_events.assert_called_once()
    entry = put_events.call_args.kwargs["Entries"][0]
    assert entry["DetailType"] == "AIAnalysisComplete"
    assert entry["Source"] == "guardrail"
