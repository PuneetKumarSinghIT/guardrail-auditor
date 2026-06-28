"""Tests for the failure Lambda — ECS exit!=0 / DLQ -> FAILED -> ScanFailed."""
import json
import os
from unittest.mock import patch

import boto3
from moto import mock_aws

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("SCAN_JOBS_TABLE", "scan-jobs-test")
os.environ.setdefault("EVENT_BUS_NAME", "default")

from src.handlers import failure_handler


def _jobs_table(ddb):
    return ddb.create_table(
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


def _ecs_event(job_id="job-fail", stage="rules-engine", exit_code=1):
    return {
        "detail-type": "ECS Task State Change",
        "detail": {
            "taskDefinitionArn": f"arn:aws:ecs:us-east-1:1:task-definition/guardrail-{stage}-dev:3",
            "stoppedReason": "Essential container exited",
            "containers": [{"name": stage, "exitCode": exit_code, "reason": "OOM"}],
            "overrides": {
                "containerOverrides": [
                    {"name": stage, "environment": [{"name": "SCAN_JOB_ID", "value": job_id}]}
                ]
            },
        },
    }


@mock_aws
def test_ecs_exit_nonzero_marks_failed():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    jobs = _jobs_table(ddb)
    jobs.put_item(Item={
        "scan_job_id": "job-fail", "created_at": "2026-06-28T00:00:00+00:00", "status": "SCANNING",
    })

    with patch.object(failure_handler.events_client, "put_events"):
        result = failure_handler.handler(_ecs_event(), None)

    assert result["statusCode"] == 200
    item = jobs.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("scan_job_id").eq("job-fail")
    )["Items"][0]
    assert item["status"] == "FAILED"
    assert item["failed_stage"] == "rules-engine"
    assert "exitCode=1" in item["error_message"]


@mock_aws
def test_scan_failed_event_published():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    jobs = _jobs_table(ddb)
    jobs.put_item(Item={
        "scan_job_id": "job-fail", "created_at": "2026-06-28T00:00:00+00:00", "status": "SCANNING",
    })

    with patch.object(failure_handler.events_client, "put_events") as pe:
        failure_handler.handler(_ecs_event(job_id="job-fail", stage="checkov"), None)

    entries = pe.call_args.kwargs["Entries"]
    assert entries[0]["DetailType"] == "ScanFailed"
    detail = json.loads(entries[0]["Detail"])
    assert detail["scan_job_id"] == "job-fail"
    assert detail["failed_stage"] == "checkov"


@mock_aws
def test_sns_dlq_path_marks_failed_checkov():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    jobs = _jobs_table(ddb)
    jobs.put_item(Item={
        "scan_job_id": "job-dlq", "created_at": "2026-06-28T00:00:00+00:00", "status": "SCANNING",
    })
    sns_event = {"Records": [{"Sns": {"Message": json.dumps({"scan_job_id": "job-dlq"})}}]}

    with patch.object(failure_handler.events_client, "put_events") as pe:
        result = failure_handler.handler(sns_event, None)

    assert result["statusCode"] == 200
    item = jobs.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("scan_job_id").eq("job-dlq")
    )["Items"][0]
    assert item["status"] == "FAILED"
    assert item["failed_stage"] == "checkov"
    assert json.loads(pe.call_args.kwargs["Entries"][0]["Detail"])["scan_job_id"] == "job-dlq"


@mock_aws
def test_failed_stage_identified_from_container_name():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    jobs = _jobs_table(ddb)
    jobs.put_item(Item={
        "scan_job_id": "job-2", "created_at": "2026-06-28T00:00:00+00:00", "status": "SCANNING",
    })

    with patch.object(failure_handler.events_client, "put_events"):
        failure_handler.handler(_ecs_event(job_id="job-2", stage="rules-engine", exit_code=137), None)

    item = jobs.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("scan_job_id").eq("job-2")
    )["Items"][0]
    assert item["failed_stage"] == "rules-engine"
    assert "exitCode=137" in item["error_message"]
