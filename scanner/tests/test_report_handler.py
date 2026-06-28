"""Tests for the report Lambda — AIAnalysisComplete -> PDF in S3 -> ReportGenerated."""
import json
import os
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("SCAN_JOBS_TABLE", "scan-jobs-test")
os.environ.setdefault("FINDINGS_TABLE", "findings-test")
os.environ.setdefault("REPORTS_BUCKET", "guardrail-scan-reports-test")
os.environ.setdefault("EVENT_BUS_NAME", "default")

from src.handlers import report_handler


def _setup(ddb):
    jobs = ddb.create_table(
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
    return jobs, findings


def _seed(jobs, findings, job_id="job-rep"):
    jobs.put_item(Item={
        "scan_job_id": job_id,
        "created_at": "2026-06-28T00:00:00+00:00",
        "status": "AI_COMPLETE",
        "file_name": "demo.tf",
        "risk_score": 60,
    })
    findings.put_item(Item={
        "scan_job_id": job_id, "finding_id": "f1", "rule_id": "S3-001",
        "severity": "CRITICAL", "resource_name": "b", "resource_type": "aws_s3_bucket",
        "line_number": 1, "ai_explanation": "bad", "ai_fix_code": "fix",
    })


def _event(job_id="job-rep"):
    return {"detail-type": "AIAnalysisComplete", "detail": {"scan_job_id": job_id}}


@mock_aws
def test_pdf_uploaded_to_s3():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="guardrail-scan-reports-test")
    jobs, findings = _setup(ddb)
    _seed(jobs, findings)

    with patch.object(report_handler.events_client, "put_events") as pe:
        result = report_handler.handler(_event(), None)

    assert result["statusCode"] == 200
    obj = s3.get_object(Bucket="guardrail-scan-reports-test", Key="job-rep/report.pdf")
    assert obj["Body"].read().startswith(b"%PDF")
    assert pe.called


@mock_aws
def test_scan_job_updated_with_report_key():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="guardrail-scan-reports-test")
    jobs, findings = _setup(ddb)
    _seed(jobs, findings)

    with patch.object(report_handler.events_client, "put_events"):
        report_handler.handler(_event(), None)

    item = jobs.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("scan_job_id").eq("job-rep")
    )["Items"][0]
    assert item["report_s3_key"] == "job-rep/report.pdf"
    assert item["status"] == "REPORT_COMPLETE"


@mock_aws
def test_report_generated_event_published():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="guardrail-scan-reports-test")
    jobs, findings = _setup(ddb)
    _seed(jobs, findings)

    with patch.object(report_handler.events_client, "put_events") as pe:
        report_handler.handler(_event(), None)

    entries = pe.call_args.kwargs["Entries"]
    assert entries[0]["DetailType"] == "ReportGenerated"
    detail = json.loads(entries[0]["Detail"])
    assert detail["scan_job_id"] == "job-rep"
    assert detail["report_s3_key"] == "job-rep/report.pdf"


@mock_aws
def test_missing_scan_job_id_returns_400():
    result = report_handler.handler({"detail": {}}, None)
    assert result["statusCode"] == 400
