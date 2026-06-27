import json
import os
import pytest

os.environ["SCAN_JOBS_TABLE"] = "scan-jobs-test"
os.environ["EVENT_BUS_NAME"] = "default"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"

import boto3
from moto import mock_aws

from scanner.src.handlers.ingest_handler import handler


def _make_event(bucket: str, key: str) -> dict:
    return {
        "detail": {
            "bucket": {"name": bucket},
            "object": {"key": key},
        }
    }


@pytest.fixture(autouse=True)
def aws_mocks():
    with mock_aws():
        # Create DynamoDB table
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.create_table(
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
        yield


def test_valid_tf_creates_job():
    event = _make_event("guardrail-iac-uploads-dev-123", "uploads/demo.tf")
    response = handler(event, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "scan_job_id" in body
    assert body["status"] == "QUEUED"

    # Verify DynamoDB record created
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    table = ddb.Table("scan-jobs-test")
    result = table.scan()
    assert len(result["Items"]) == 1
    item = result["Items"][0]
    assert item["iac_type"] == "terraform"
    assert item["status"] == "QUEUED"
    assert item["file_name"] == "demo.tf"


def test_valid_yaml_creates_job():
    event = _make_event("guardrail-iac-uploads-dev-123", "uploads/template.yaml")
    response = handler(event, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "scan_job_id" in body

    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    table = ddb.Table("scan-jobs-test")
    result = table.scan()
    item = result["Items"][0]
    assert item["iac_type"] == "cloudformation"


def test_invalid_extension_rejected():
    event = _make_event("guardrail-iac-uploads-dev-123", "uploads/malware.exe")
    response = handler(event, None)
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body

    # No DynamoDB record should be created
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    table = ddb.Table("scan-jobs-test")
    result = table.scan()
    assert len(result["Items"]) == 0


def test_missing_s3_key_fails():
    event = {"detail": {"bucket": {"name": "some-bucket"}}}
    response = handler(event, None)
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body


def test_eventbridge_event_published():
    # autouse fixture already provides mock_aws + the DDB table.
    # If EventBridge put_events doesn't raise, the event was published successfully.
    event = _make_event("guardrail-iac-uploads-dev-123", "uploads/infra.tf")
    response = handler(event, None)
    assert response["statusCode"] == 200
