"""API route tests — drive app.handler end to end with moto-backed DynamoDB + S3.

Auth is stubbed (get_claims patched) for the happy-path routes; the no-auth test
exercises the real middleware to confirm a missing JWT yields 401.
"""
import json
import os

# Env must be set before importing the route modules (table/bucket names are read
# at import time).
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("SCAN_JOBS_TABLE", "scan-jobs-test")
os.environ.setdefault("FINDINGS_TABLE", "findings-test")
os.environ.setdefault("UPLOAD_BUCKET", "uploads-test")
os.environ.setdefault("REPORTS_BUCKET", "reports-test")
os.environ.setdefault("COGNITO_USER_POOL_ID", "us-east-1_TESTPOOL")

import boto3
from moto import mock_aws

from src import app

_CLAIMS = {"sub": "user-123"}


def _setup_aws():
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
    ddb.create_table(
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
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="uploads-test")
    s3.create_bucket(Bucket="reports-test")
    return ddb


def _seed_job(ddb, scan_job_id, created_at, **extra):
    item = {
        "scan_job_id": scan_job_id,
        "created_at": created_at,
        "status": "COMPLETE",
        "file_name": f"{scan_job_id}.tf",
        "risk_score": 42,
        "finding_counts": {"CRITICAL": 1, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
    }
    item.update(extra)
    ddb.Table("scan-jobs-test").put_item(Item=item)


def _event(method, resource, path_params=None, body=None, with_auth=True):
    return {
        "httpMethod": method,
        "resource": resource,
        "headers": {"Authorization": "Bearer fake"} if with_auth else {},
        "pathParameters": path_params,
        "body": json.dumps(body) if body is not None else None,
    }


@mock_aws
def test_post_scan_returns_presigned_url(monkeypatch):
    _setup_aws()
    monkeypatch.setattr(app, "get_claims", lambda e: _CLAIMS)
    resp = app.handler(_event("POST", "/v1/scans", body={"file_name": "demo.tf"}), None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["scan_job_id"]
    assert "presigned_url" in body
    # The QUEUED record was created, keyed by the same id embedded in the URL.
    items = boto3.resource("dynamodb", region_name="us-east-1").Table("scan-jobs-test").scan()["Items"]
    assert len(items) == 1
    assert items[0]["status"] == "QUEUED"
    assert items[0]["s3_key"] == f"uploads/{body['scan_job_id']}/demo.tf"


@mock_aws
def test_list_scans_sorted_desc(monkeypatch):
    ddb = _setup_aws()
    monkeypatch.setattr(app, "get_claims", lambda e: _CLAIMS)
    _seed_job(ddb, "job-old", "2026-01-01T00:00:00+00:00")
    _seed_job(ddb, "job-new", "2026-06-01T00:00:00+00:00")
    resp = app.handler(_event("GET", "/v1/scans"), None)
    assert resp["statusCode"] == 200
    rows = json.loads(resp["body"])
    assert [r["scan_job_id"] for r in rows] == ["job-new", "job-old"]
    assert rows[0]["risk_score"] == 42  # Decimal coerced to int


@mock_aws
def test_get_scan_detail_includes_findings(monkeypatch):
    ddb = _setup_aws()
    monkeypatch.setattr(app, "get_claims", lambda e: _CLAIMS)
    _seed_job(ddb, "job-1", "2026-01-01T00:00:00+00:00")
    ddb.Table("findings-test").put_item(
        Item={
            "scan_job_id": "job-1",
            "finding_id": "f1",
            "rule_id": "S3-001",
            "severity": "CRITICAL",
            "ai_explanation": "Public bucket.",
        }
    )
    resp = app.handler(
        _event("GET", "/v1/scans/{scan_job_id}", path_params={"scan_job_id": "job-1"}), None
    )
    assert resp["statusCode"] == 200
    detail = json.loads(resp["body"])
    assert detail["scan_job_id"] == "job-1"
    assert len(detail["findings"]) == 1
    assert detail["findings"][0]["rule_id"] == "S3-001"


@mock_aws
def test_get_report_url(monkeypatch):
    ddb = _setup_aws()
    monkeypatch.setattr(app, "get_claims", lambda e: _CLAIMS)
    _seed_job(ddb, "job-1", "2026-01-01T00:00:00+00:00", report_s3_key="job-1/report.pdf")
    resp = app.handler(
        _event(
            "GET",
            "/v1/scans/{scan_job_id}/report",
            path_params={"scan_job_id": "job-1"},
        ),
        None,
    )
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "report_url" in body
    assert "job-1/report.pdf" in body["report_url"]


@mock_aws
def test_request_without_jwt_returns_401():
    _setup_aws()
    # No monkeypatch — the real Cognito middleware runs and rejects the missing token.
    resp = app.handler(_event("GET", "/v1/scans", with_auth=False), None)
    assert resp["statusCode"] == 401
    assert json.loads(resp["body"])["error"] == "Unauthorized"
