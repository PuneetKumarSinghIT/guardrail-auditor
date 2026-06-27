import json
import os
import uuid
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

# Set env vars BEFORE importing the module
os.environ.setdefault("SCAN_JOBS_TABLE", "scan-jobs-test")
os.environ.setdefault("FINDINGS_TABLE", "findings-test")
os.environ.setdefault("RULES_TABLE", "rules-catalog-test")
os.environ.setdefault("UPLOAD_BUCKET", "test-bucket")
os.environ.setdefault("EVENT_BUS_NAME", "default")

from scanner.src.handlers import rules_engine


SAMPLE_RULES = [
    {"rule_id": "S3-001", "severity": "CRITICAL", "category": "S3", "enabled": True},
    {"rule_id": "S3-003", "severity": "MEDIUM",   "category": "S3", "enabled": True},
    {"rule_id": "SG-001", "severity": "CRITICAL", "category": "NETWORK", "enabled": True},
    {"rule_id": "IAM-001", "severity": "HIGH",    "category": "IAM", "enabled": True},
    {"rule_id": "ENC-001", "severity": "HIGH",    "category": "ENCRYPTION", "enabled": True},
    {"rule_id": "LOG-001", "severity": "HIGH",    "category": "LOGGING", "enabled": False},  # disabled
]

PUBLIC_S3_TF = b'''
resource "aws_s3_bucket" "bad_bucket" {
  bucket = "bad-bucket"
  acl    = "public-read"
}
'''

OPEN_SG_TF = b'''
resource "aws_security_group" "open_sg" {
  name = "open-sg"
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
'''

CFN_PUBLIC_S3 = b"""
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  BadBucket:
    Type: AWS::S3::Bucket
    Properties:
      AccessControl: PublicRead
"""


def test_apply_terraform_s3_public_detects_violation():
    resources = {"aws_s3_bucket": {"bad_bucket": {"acl": ["public-read"]}}}
    findings = rules_engine._apply_terraform_rules(resources, SAMPLE_RULES, "job-123")
    rule_ids = [f.rule_id for f in findings]
    assert "S3-001" in rule_ids


def test_apply_terraform_disabled_rule_not_applied():
    """LOG-001 is disabled in SAMPLE_RULES — no finding should be created."""
    resources = {"aws_cloudtrail": {"trail": {"enable_logging": [False]}}}
    findings = rules_engine._apply_terraform_rules(resources, SAMPLE_RULES, "job-123")
    rule_ids = [f.rule_id for f in findings]
    assert "LOG-001" not in rule_ids


def test_apply_terraform_sg_ssh_open_detects_violation():
    resources = {
        "aws_security_group": {
            "open_sg": {
                "ingress": [{"from_port": [22], "to_port": [22], "protocol": ["tcp"], "cidr_blocks": [["0.0.0.0/0"]]}]
            }
        }
    }
    findings = rules_engine._apply_terraform_rules(resources, SAMPLE_RULES, "job-123")
    rule_ids = [f.rule_id for f in findings]
    assert "SG-001" in rule_ids


def test_apply_cloudformation_s3_public_detects_violation():
    resources = {"AWS::S3::Bucket": [{"Name": "BadBucket", "Properties": {"AccessControl": "PublicRead"}}]}
    findings = rules_engine._apply_cloudformation_rules(resources, SAMPLE_RULES, "job-123")
    rule_ids = [f.rule_id for f in findings]
    assert "S3-001" in rule_ids


def test_apply_terraform_clean_resources_no_findings():
    resources = {
        "aws_s3_bucket": {"good_bucket": {
            "acl": ["private"],
            "versioning": [{"enabled": [True]}],
            "server_side_encryption_configuration": [{"rule": []}],
            "logging": [{"target_bucket": ["log-bucket"]}],
        }}
    }
    findings = rules_engine._apply_terraform_rules(resources, SAMPLE_RULES, "job-123")
    rule_ids = [f.rule_id for f in findings]
    # S3-001 should NOT fire for private ACL
    assert "S3-001" not in rule_ids


@mock_aws
def test_handler_writes_findings_to_dynamodb():
    """Integration test: handler uses S3 content, scans, writes findings to DDB."""
    from unittest.mock import patch, MagicMock

    ddb = boto3.resource("dynamodb", region_name="us-east-1")
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
    scan_jobs_table.put_item(Item={
        "scan_job_id": "test-job-123",
        "created_at": "2026-01-01T00:00:00+00:00",
        "status": "QUEUED",
        "file_name": "test.tf",
        "iac_type": "terraform",
    })

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

    rules_table = ddb.create_table(
        TableName="rules-catalog-test",
        KeySchema=[{"AttributeName": "rule_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "rule_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    for rule in SAMPLE_RULES:
        rules_table.put_item(Item=rule)

    # Patch s3_client.get_object to return PUBLIC_S3_TF content directly
    # (avoids issues with moto S3 not intercepting pre-created module-level clients)
    mock_s3_body = MagicMock()
    mock_s3_body.read.return_value = PUBLIC_S3_TF
    mock_s3_response = {"Body": mock_s3_body}

    event = {
        "source": "guardrail",
        "detail-type": "ScanRequested",
        "detail": {
            "scan_job_id": "test-job-123",
            "s3_key": "uploads/test.tf",
            "s3_bucket": "test-bucket",
            "iac_type": "terraform",
        },
    }

    # Patch both parse_terraform and s3_client.get_object to isolate from parser issues
    with patch("scanner.src.handlers.rules_engine.parse_terraform") as mock_parse_tf, \
         patch.object(rules_engine.s3_client, "get_object", return_value=mock_s3_response):
        # Return a resource dict that will trigger S3-001
        mock_parse_tf.return_value = {"aws_s3_bucket": {"bad_bucket": {"acl": ["public-read"]}}}
        result = rules_engine.handler(event, None)

    assert result["statusCode"] == 200

    items = findings_table.scan()["Items"]
    assert len(items) >= 1
    rule_ids_found = {item["rule_id"] for item in items}
    assert "S3-001" in rule_ids_found


def test_apply_cloudformation_sg_ssh_detects_violation():
    resources = {
        "AWS::EC2::SecurityGroup": [
            {
                "Name": "OpenSG",
                "Properties": {
                    "SecurityGroupIngress": [
                        {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "CidrIp": "0.0.0.0/0"}
                    ]
                }
            }
        ]
    }
    findings = rules_engine._apply_cloudformation_rules(resources, SAMPLE_RULES, "job-cfn-sg")
    rule_ids = [f.rule_id for f in findings]
    assert "SG-001" in rule_ids


def test_apply_terraform_iam_wildcard_detects_violation():
    resources = {
        "aws_iam_policy": {
            "bad_policy": {
                "policy": [json.dumps({
                    "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]
                })]
            }
        }
    }
    # Use rules that include IAM-001 and IAM-002
    iam_rules = [
        {"rule_id": "IAM-001", "severity": "HIGH", "category": "IAM", "enabled": True},
        {"rule_id": "IAM-002", "severity": "HIGH", "category": "IAM", "enabled": True},
    ]
    findings = rules_engine._apply_terraform_rules(resources, iam_rules, "job-iam")
    rule_ids = [f.rule_id for f in findings]
    assert "IAM-001" in rule_ids
    assert "IAM-002" in rule_ids


def test_apply_terraform_ebs_unencrypted_detects_violation():
    resources = {
        "aws_ebs_volume": {
            "unencrypted_vol": {
                "size": [20],
                "encrypted": [False],
            }
        }
    }
    enc_rules = [
        {"rule_id": "ENC-001", "severity": "HIGH", "category": "ENCRYPTION", "enabled": True},
    ]
    findings = rules_engine._apply_terraform_rules(resources, enc_rules, "job-enc")
    rule_ids = [f.rule_id for f in findings]
    assert "ENC-001" in rule_ids
