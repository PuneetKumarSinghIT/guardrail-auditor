import json
import os
import uuid
from decimal import Decimal

import boto3
import pytest
from moto import mock_aws

os.environ.setdefault("SCAN_JOBS_TABLE", "scan-jobs-test")
os.environ.setdefault("FINDINGS_TABLE", "findings-test")
os.environ.setdefault("EVENT_BUS_NAME", "default")

from scanner.src.handlers import aggregator


def _make_sqs_event(scan_job_id: str, findings: list) -> dict:
    return {
        "Records": [
            {
                "body": json.dumps({
                    "scan_job_id": scan_job_id,
                    "source": "checkov",
                    "findings": findings,
                })
            }
        ]
    }


def _setup_tables(ddb):
    scan_jobs_table = ddb.create_table(
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
    findings_table = ddb.create_table(
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
    return scan_jobs_table, findings_table


@mock_aws
def test_new_findings_written_to_dynamodb():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    scan_jobs_table, findings_table = _setup_tables(ddb)
    scan_jobs_table.put_item(Item={
        "scan_job_id": "job-001",
        "created_at": "2026-01-01T00:00:00+00:00",
        "status": "SCANNING",
        "iac_type": "terraform",
    })

    findings = [
        {"rule_id": "S3-001", "severity": "CRITICAL", "resource_name": "aws_s3_bucket.bad", "resource_type": "aws_s3_bucket", "line_number": 1},
        {"rule_id": "SG-001", "severity": "CRITICAL", "resource_name": "aws_security_group.open", "resource_type": "aws_security_group", "line_number": 10},
    ]
    event = _make_sqs_event("job-001", findings)
    result = aggregator.handler(event, None)
    assert result["statusCode"] == 200

    items = findings_table.scan()["Items"]
    assert len(items) == 2
    rule_ids = {item["rule_id"] for item in items}
    assert "S3-001" in rule_ids
    assert "SG-001" in rule_ids


@mock_aws
def test_duplicate_findings_not_written():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    scan_jobs_table, findings_table = _setup_tables(ddb)
    scan_jobs_table.put_item(Item={
        "scan_job_id": "job-002",
        "created_at": "2026-01-01T00:00:00+00:00",
        "status": "SCANNING",
    })

    # Pre-populate findings table with an existing finding
    findings_table.put_item(Item={
        "scan_job_id": "job-002",
        "finding_id": str(uuid.uuid4()),
        "rule_id": "S3-001",
        "severity": "CRITICAL",
        "resource_name": "aws_s3_bucket.bad",
        "resource_type": "aws_s3_bucket",
    })

    # Same finding from checkov — should NOT be written again
    findings = [
        {"rule_id": "S3-001", "severity": "CRITICAL", "resource_name": "aws_s3_bucket.bad", "resource_type": "aws_s3_bucket", "line_number": 1},
    ]
    event = _make_sqs_event("job-002", findings)
    aggregator.handler(event, None)

    items = findings_table.scan()["Items"]
    s3_findings = [i for i in items if i["rule_id"] == "S3-001"]
    assert len(s3_findings) == 1  # still only 1, not 2


@mock_aws
def test_scan_complete_event_published_and_status_updated():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    scan_jobs_table, findings_table = _setup_tables(ddb)
    scan_jobs_table.put_item(Item={
        "scan_job_id": "job-003",
        "created_at": "2026-01-01T00:00:00+00:00",
        "status": "SCANNING",
    })

    findings = [
        {"rule_id": "ENC-001", "severity": "HIGH", "resource_name": "aws_ebs_volume.unencrypted", "resource_type": "aws_ebs_volume", "line_number": 5},
    ]
    event = _make_sqs_event("job-003", findings)
    result = aggregator.handler(event, None)
    assert result["statusCode"] == 200

    # Verify scan-jobs status updated to COMPLETE
    updated = scan_jobs_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("scan_job_id").eq("job-003")
    )["Items"][0]
    assert updated["status"] == "COMPLETE"
    assert updated["finding_counts"]["HIGH"] == Decimal("1")
