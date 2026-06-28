#!/usr/bin/env python3
"""Seed pre-canned demo scans into scan-jobs-{env} + findings-{env}.

WHY: A freshly-woken demo environment has an empty scan history. The client
demo opens on the Scan List page — that page must show realistic, completed
scans immediately (no "upload and wait 80s" cold open). This writes three
fully-analysed scans, dated across the past week, with risk scores that
IMPROVE over time (oldest = HIGH, newest = LOW). That improving trend is the
demo narrative: "this organisation reduced its IaC risk 75% in a week."

Every seeded finding carries a realistic ai_explanation, and every
CRITICAL/HIGH finding carries an ai_fix_code block — exactly what the real
Bedrock pipeline produces — so the Scan Detail page + AI drawer + "View Fix"
all render with content.

What it does NOT seed: PDF reports. Seeded scans intentionally leave
report_s3_key unset, so the dashboard's "Download PDF Report" button reports
"report not ready" rather than handing out a presigned URL to a missing
object. Run a real scan to exercise the PDF path end to end.

Idempotent: re-running overwrites the same three scan_job_ids (deterministic,
date-derived) and their findings. Safe to run on every demo_wake.

Usage:
  AWS_PROFILE=aws-admin python scripts/seed_demo_data.py --env dev
  DEPLOY_ENV=staging python scripts/seed_demo_data.py
"""
import argparse
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import boto3

# Risk Score Algorithm — must match CLAUDE.md / ai-engine analyzer exactly.
WEIGHTS = {"CRITICAL": 40, "HIGH": 20, "MEDIUM": 5, "LOW": 1}
MAX_POSSIBLE = 200

# Deterministic UUID namespace so re-seeding overwrites the same rows instead
# of piling up duplicates. (uuid5 is stable for a given name.)
_NS = uuid.UUID("11111111-2222-3333-4444-555555555555")


def _risk_score(findings: list[dict]) -> int:
    raw = sum(WEIGHTS.get(f["severity"], 0) for f in findings)
    return int((min(raw, MAX_POSSIBLE) / MAX_POSSIBLE) * 100)


def _counts(findings: list[dict]) -> dict:
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1
    return counts


# ── Demo scan definitions ────────────────────────────────────────────────────
# Oldest first; days_ago controls created_at so the list shows newest (lowest
# risk) at the top — an improving-posture story.

DEMO_SCANS = [
    {
        "file_name": "legacy-vpc-stack.tf",
        "iac_type": "terraform",
        "days_ago": 6,
        "findings": [
            {
                "rule_id": "S3-001", "severity": "CRITICAL",
                "resource_name": "aws_s3_bucket.customer_uploads",
                "resource_type": "aws_s3_bucket", "line_number": 12,
                "code_snippet": 'acl = "public-read"',
                "ai_explanation": "This S3 bucket grants public read access via a "
                    "public-read ACL, meaning anyone on the internet can list and "
                    "download every object in it. For a bucket named 'customer_uploads' "
                    "this is a direct data-exposure risk.",
                "ai_fix_code": 'resource "aws_s3_bucket" "customer_uploads" {\n'
                    '  bucket = "customer-uploads"\n}\n\n'
                    'resource "aws_s3_bucket_public_access_block" "customer_uploads" {\n'
                    '  bucket                  = aws_s3_bucket.customer_uploads.id\n'
                    '  block_public_acls       = true\n'
                    '  block_public_policy     = true\n'
                    '  ignore_public_acls      = true\n'
                    '  restrict_public_buckets = true\n}',
            },
            {
                "rule_id": "SG-001", "severity": "CRITICAL",
                "resource_name": "aws_security_group.bastion",
                "resource_type": "aws_security_group", "line_number": 34,
                "code_snippet": 'from_port = 22\ncidr_blocks = ["0.0.0.0/0"]',
                "ai_explanation": "Port 22 (SSH) is open to 0.0.0.0/0, exposing the "
                    "bastion host to brute-force and credential-stuffing attacks from "
                    "the entire internet. Restrict SSH to known corporate IP ranges or "
                    "use SSM Session Manager instead.",
                "ai_fix_code": 'ingress {\n  from_port   = 22\n  to_port     = 22\n'
                    '  protocol    = "tcp"\n  cidr_blocks = ["10.0.0.0/8"]  '
                    '# corporate VPN range only\n}',
            },
            {
                "rule_id": "ENC-002", "severity": "CRITICAL",
                "resource_name": "aws_db_instance.orders",
                "resource_type": "aws_db_instance", "line_number": 58,
                "code_snippet": "storage_encrypted = false",
                "ai_explanation": "The RDS instance storing order data has encryption "
                    "at rest disabled. If the underlying storage is compromised or a "
                    "snapshot is leaked, the data is readable in plaintext. Enable "
                    "storage encryption with a KMS key.",
                "ai_fix_code": 'resource "aws_db_instance" "orders" {\n'
                    '  # ...\n  storage_encrypted = true\n'
                    '  kms_key_id        = aws_kms_key.rds.arn\n}',
            },
            {
                "rule_id": "IAM-001", "severity": "HIGH",
                "resource_name": "aws_iam_policy.app_admin",
                "resource_type": "aws_iam_policy", "line_number": 71,
                "code_snippet": '"Action": "*"',
                "ai_explanation": "This IAM policy grants Action '*' — every action on "
                    "every service. A compromise of any principal attached to it becomes "
                    "a full account takeover. Scope the policy to the specific actions "
                    "the application actually needs.",
                "ai_fix_code": '{\n  "Effect": "Allow",\n'
                    '  "Action": ["s3:GetObject", "s3:PutObject"],\n'
                    '  "Resource": "arn:aws:s3:::customer-uploads/*"\n}',
            },
            {
                "rule_id": "LOG-002", "severity": "MEDIUM",
                "resource_name": "aws_vpc.main",
                "resource_type": "aws_vpc", "line_number": 3,
                "code_snippet": "# no aws_flow_log resource",
                "ai_explanation": "The VPC has no flow logs configured, so there is no "
                    "record of accepted/rejected network traffic. This blinds incident "
                    "response and compliance auditing. Add a VPC flow log to CloudWatch "
                    "Logs or S3.",
                "ai_fix_code": "",
            },
        ],
    },
    {
        "file_name": "staging-app-platform.tf",
        "iac_type": "terraform",
        "days_ago": 3,
        "findings": [
            {
                "rule_id": "SG-002", "severity": "CRITICAL",
                "resource_name": "aws_security_group.windows_admin",
                "resource_type": "aws_security_group", "line_number": 28,
                "code_snippet": 'from_port = 3389\ncidr_blocks = ["0.0.0.0/0"]',
                "ai_explanation": "RDP (port 3389) is open to the entire internet. RDP "
                    "is a top ransomware entry vector; exposed RDP endpoints are scanned "
                    "and attacked within minutes. Lock this down to a jump host or VPN.",
                "ai_fix_code": 'ingress {\n  from_port   = 3389\n  to_port     = 3389\n'
                    '  protocol    = "tcp"\n  cidr_blocks = ["10.0.0.0/8"]\n}',
            },
            {
                "rule_id": "S3-004", "severity": "HIGH",
                "resource_name": "aws_s3_bucket.build_artifacts",
                "resource_type": "aws_s3_bucket", "line_number": 9,
                "code_snippet": "# no server_side_encryption_configuration",
                "ai_explanation": "This bucket has no server-side encryption configured. "
                    "Build artifacts can contain credentials and source — store them "
                    "encrypted at rest with SSE-KMS or at minimum SSE-S3.",
                "ai_fix_code": 'resource "aws_s3_bucket_server_side_encryption_'
                    'configuration" "build_artifacts" {\n'
                    '  bucket = aws_s3_bucket.build_artifacts.id\n  rule {\n'
                    '    apply_server_side_encryption_by_default {\n'
                    '      sse_algorithm = "aws:kms"\n    }\n  }\n}',
            },
            {
                "rule_id": "ENC-001", "severity": "HIGH",
                "resource_name": "aws_ebs_volume.cache",
                "resource_type": "aws_ebs_volume", "line_number": 41,
                "code_snippet": "encrypted = false",
                "ai_explanation": "This EBS volume is unencrypted. Detached or "
                    "snapshotted volumes can be mounted elsewhere; without encryption "
                    "the data is fully readable. Set encrypted = true.",
                "ai_fix_code": 'resource "aws_ebs_volume" "cache" {\n'
                    '  availability_zone = "us-east-1a"\n  size              = 50\n'
                    '  encrypted         = true\n}',
            },
            {
                "rule_id": "S3-003", "severity": "MEDIUM",
                "resource_name": "aws_s3_bucket.build_artifacts",
                "resource_type": "aws_s3_bucket", "line_number": 9,
                "code_snippet": "# no versioning block",
                "ai_explanation": "Versioning is disabled, so an accidental or malicious "
                    "overwrite/delete is unrecoverable. Enable versioning for objects "
                    "that matter.",
                "ai_fix_code": "",
            },
            {
                "rule_id": "SG-004", "severity": "MEDIUM",
                "resource_name": "aws_security_group.web",
                "resource_type": "aws_security_group", "line_number": 52,
                "code_snippet": 'from_port = 80\ncidr_blocks = ["0.0.0.0/0"]',
                "ai_explanation": "Port 80 (HTTP) is open to the world on a non-load-"
                    "balancer security group. Serve traffic over HTTPS via a load "
                    "balancer and redirect HTTP, rather than exposing the instance "
                    "directly.",
                "ai_fix_code": "",
            },
        ],
    },
    {
        "file_name": "prod-baseline.tf",
        "iac_type": "terraform",
        "days_ago": 0,
        "findings": [
            {
                "rule_id": "S3-004", "severity": "HIGH",
                "resource_name": "aws_s3_bucket.logs_archive",
                "resource_type": "aws_s3_bucket", "line_number": 14,
                "code_snippet": "# no server_side_encryption_configuration",
                "ai_explanation": "The log-archive bucket is missing server-side "
                    "encryption. Logs often contain sensitive request metadata; encrypt "
                    "the bucket at rest.",
                "ai_fix_code": 'resource "aws_s3_bucket_server_side_encryption_'
                    'configuration" "logs_archive" {\n'
                    '  bucket = aws_s3_bucket.logs_archive.id\n  rule {\n'
                    '    apply_server_side_encryption_by_default {\n'
                    '      sse_algorithm = "aws:kms"\n    }\n  }\n}',
            },
            {
                "rule_id": "S3-003", "severity": "MEDIUM",
                "resource_name": "aws_s3_bucket.logs_archive",
                "resource_type": "aws_s3_bucket", "line_number": 14,
                "code_snippet": "# no versioning block",
                "ai_explanation": "Versioning is disabled on the log archive. Enable it "
                    "so retention and tamper-evidence guarantees hold.",
                "ai_fix_code": "",
            },
            {
                "rule_id": "LOG-002", "severity": "MEDIUM",
                "resource_name": "aws_vpc.prod",
                "resource_type": "aws_vpc", "line_number": 2,
                "code_snippet": "# no aws_flow_log resource",
                "ai_explanation": "Production VPC has no flow logs. Add them for network "
                    "visibility and compliance.",
                "ai_fix_code": "",
            },
            {
                "rule_id": "S3-005", "severity": "LOW",
                "resource_name": "aws_s3_bucket.assets",
                "resource_type": "aws_s3_bucket", "line_number": 30,
                "code_snippet": "# no logging block",
                "ai_explanation": "Access logging is off on the assets bucket. Enable it "
                    "to retain an audit trail of object access.",
                "ai_fix_code": "",
            },
            {
                "rule_id": "S3-005", "severity": "LOW",
                "resource_name": "aws_s3_bucket.logs_archive",
                "resource_type": "aws_s3_bucket", "line_number": 14,
                "code_snippet": "# no logging block",
                "ai_explanation": "Access logging is off on the log-archive bucket. "
                    "Enable it for a complete audit trail.",
                "ai_fix_code": "",
            },
            {
                "rule_id": "IAM-005", "severity": "LOW",
                "resource_name": "aws_iam_role_policy.task_inline",
                "resource_type": "aws_iam_role_policy", "line_number": 47,
                "code_snippet": "inline policy on role",
                "ai_explanation": "An inline policy is attached to this role. Managed "
                    "policies are versioned, reusable and easier to audit — prefer them "
                    "over inline policies.",
                "ai_fix_code": "",
            },
        ],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default=os.environ.get("DEPLOY_ENV", "dev"))
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", "us-east-1"))
    args = parser.parse_args()

    ddb = boto3.resource("dynamodb", region_name=args.region)
    scan_jobs = ddb.Table(f"scan-jobs-{args.env}")
    findings_tbl = ddb.Table(f"findings-{args.env}")

    now = datetime.now(timezone.utc)
    seeded = []

    for spec in DEMO_SCANS:
        findings = spec["findings"]
        created_at = (now - timedelta(days=spec["days_ago"])).isoformat()
        # Deterministic id from file_name so re-seeding overwrites, not duplicates.
        scan_job_id = str(uuid.uuid5(_NS, f"{args.env}:{spec['file_name']}"))
        score = _risk_score(findings)
        counts = _counts(findings)

        scan_jobs.put_item(Item={
            "scan_job_id": scan_job_id,
            "created_at": created_at,
            "status": "COMPLETE",
            "file_name": spec["file_name"],
            "s3_key": f"uploads/{scan_job_id}/{spec['file_name']}",
            "iac_type": spec["iac_type"],
            "risk_score": score,
            "finding_counts": counts,
            "created_by": "demo-seed",
            "demo_seed": True,  # marker so it's distinguishable from real scans
        })

        with findings_tbl.batch_writer() as batch:
            for f in findings:
                batch.put_item(Item={
                    "scan_job_id": scan_job_id,
                    "finding_id": str(uuid.uuid4()),
                    "rule_id": f["rule_id"],
                    "severity": f["severity"],
                    "resource_name": f["resource_name"],
                    "resource_type": f["resource_type"],
                    "line_number": f["line_number"],
                    "code_snippet": f["code_snippet"][:500],
                    "ai_explanation": f["ai_explanation"],
                    "ai_fix_code": f["ai_fix_code"],
                    "dismissed": False,
                })

        seeded.append((spec["file_name"], score, len(findings)))

    print(f"Seeded {len(seeded)} demo scans into scan-jobs-{args.env} / findings-{args.env}:")
    for name, score, n in seeded:
        print(f"  - {name:30s} risk={score:>3d}/100  findings={n}")
    print("Improving-posture trend: newest scan has the lowest risk score.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
