import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key as DdbKey, Attr

from src.models.finding import Finding
from src.parsers.terraform_parser import parse as parse_terraform
from src.parsers.cloudformation_parser import parse as parse_cloudformation

# Environment variables — fail fast at module load
SCAN_JOBS_TABLE = os.environ["SCAN_JOBS_TABLE"]
FINDINGS_TABLE = os.environ["FINDINGS_TABLE"]
RULES_TABLE = os.environ["RULES_TABLE"]
UPLOAD_BUCKET = os.environ["UPLOAD_BUCKET"]
EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME", "default")

# Clients
logger = logging.getLogger()
logger.setLevel(logging.INFO)
dynamodb = boto3.resource("dynamodb")
s3_client = boto3.client("s3")
events_client = boto3.client("events")


def main() -> None:
    """
    ECS Fargate entry point — called by src.main when MODE=rules_engine.
    Reads SCAN_JOB_ID, S3_KEY, IAC_TYPE from environment (injected at RunTask time).
    Exits 0 on success, non-zero on failure (triggers failure_handler via ECS TaskStopped event).
    """
    scan_job_id = os.environ.get("SCAN_JOB_ID")
    s3_key = os.environ.get("S3_KEY")
    s3_bucket = os.environ.get("S3_BUCKET", UPLOAD_BUCKET)
    iac_type = os.environ.get("IAC_TYPE", "terraform")

    if not scan_job_id or not s3_key:
        logger.error(json.dumps({
            "event": "missing_required_env_vars",
            "SCAN_JOB_ID": scan_job_id,
            "S3_KEY": s3_key,
        }))
        raise SystemExit(1)

    _run_scan(scan_job_id, s3_key, s3_bucket, iac_type)


def _run_scan(scan_job_id: str, s3_key: str, s3_bucket: str, iac_type: str) -> None:
    """Core scan logic — shared by ECS main() and Lambda handler()."""
    logger.info(json.dumps({
        "event": "rules_engine_started",
        "scan_job_id": scan_job_id,
        "s3_key": s3_key,
        "iac_type": iac_type,
    }))

    _update_scan_status(scan_job_id, "SCANNING")

    rules_table = dynamodb.Table(RULES_TABLE)
    rules_response = rules_table.scan(FilterExpression=Attr("enabled").eq(True))
    rules = rules_response.get("Items", [])
    logger.info(json.dumps({
        "event": "rules_loaded",
        "scan_job_id": scan_job_id,
        "rule_count": len(rules),
    }))

    s3_response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
    file_content = s3_response["Body"].read()
    logger.info(json.dumps({
        "event": "file_downloaded",
        "scan_job_id": scan_job_id,
        "file_size_bytes": len(file_content),
    }))

    if iac_type == "terraform":
        resources = parse_terraform(file_content)
        findings = _apply_terraform_rules(resources, rules, scan_job_id)
    else:
        resources = parse_cloudformation(file_content)
        findings = _apply_cloudformation_rules(resources, rules, scan_job_id)

    logger.info(json.dumps({
        "event": "iac_parsed",
        "scan_job_id": scan_job_id,
        "resource_count": sum(len(v) for v in resources.values()),
        "finding_count": len(findings),
    }))

    findings_table = dynamodb.Table(FINDINGS_TABLE)
    for finding in findings:
        findings_table.put_item(Item=finding.to_dynamodb_item())

    events_client.put_events(Entries=[{
        "Source": "guardrail",
        "DetailType": "RulesEngineDone",
        "EventBusName": EVENT_BUS_NAME,
        "Detail": json.dumps({
            "scan_job_id": scan_job_id,
            "finding_count": len(findings),
        }),
    }])
    logger.info(json.dumps({
        "event": "rules_engine_complete",
        "scan_job_id": scan_job_id,
        "finding_count": len(findings),
    }))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler — kept for tests. Production uses ECS main() entry point."""
    try:
        detail = event.get("detail", {})
        _run_scan(
            scan_job_id=detail.get("scan_job_id"),
            s3_key=detail.get("s3_key"),
            s3_bucket=detail.get("s3_bucket", UPLOAD_BUCKET),
            iac_type=detail.get("iac_type", "terraform"),
        )
        return {"statusCode": 200}
    except Exception as e:
        logger.error(json.dumps({
            "event": "rules_engine_failed",
            "error": str(e),
            "error_type": type(e).__name__,
        }))
        raise


def _apply_terraform_rules(
    resources: Dict[str, Dict[str, Dict[str, Any]]], rules: List[Dict[str, Any]], scan_job_id: str
) -> List[Finding]:
    """
    Apply Terraform-specific security rules.
    Returns list of Finding objects for violations detected.
    """
    findings = []
    rule_ids = {r["rule_id"] for r in rules if r.get("enabled", False)}

    # S3-001: Public S3 Bucket ACL
    if "S3-001" in rule_ids:
        for name, attrs in resources.get("aws_s3_bucket", {}).items():
            acl = _first(attrs.get("acl"))
            if acl in ("public-read", "public-read-write", "authenticated-read"):
                findings.append(
                    _make_finding(
                        "S3-001",
                        "CRITICAL",
                        name,
                        "aws_s3_bucket",
                        scan_job_id,
                        f'acl = "{acl}"',
                    )
                )

    # S3-002: Public S3 Bucket Policy
    if "S3-002" in rule_ids:
        for name, attrs in resources.get("aws_s3_bucket_policy", {}).items():
            policy = str(_first(attrs.get("policy", "")))
            if (
                '"Principal": "*"' in policy
                or '"Principal":"*"' in policy
                or "'Principal': '*'" in policy
            ):
                findings.append(
                    _make_finding(
                        "S3-002",
                        "CRITICAL",
                        name,
                        "aws_s3_bucket_policy",
                        scan_job_id,
                        "Public principal in policy",
                    )
                )

    # S3-003: S3 Versioning Disabled
    if "S3-003" in rule_ids:
        for name, attrs in resources.get("aws_s3_bucket", {}).items():
            versioning = attrs.get("versioning", [])
            ver_list = versioning if isinstance(versioning, list) else [versioning]
            enabled = any(
                _first(v.get("enabled", False)) for v in ver_list if isinstance(v, dict)
            )
            if not enabled:
                findings.append(
                    _make_finding(
                        "S3-003",
                        "MEDIUM",
                        name,
                        "aws_s3_bucket",
                        scan_job_id,
                        "versioning not enabled",
                    )
                )

    # S3-004: S3 Encryption Disabled
    if "S3-004" in rule_ids:
        for name, attrs in resources.get("aws_s3_bucket", {}).items():
            if not attrs.get("server_side_encryption_configuration"):
                findings.append(
                    _make_finding(
                        "S3-004",
                        "HIGH",
                        name,
                        "aws_s3_bucket",
                        scan_job_id,
                        "server_side_encryption_configuration missing",
                    )
                )

    # S3-005: S3 Logging Disabled
    if "S3-005" in rule_ids:
        for name, attrs in resources.get("aws_s3_bucket", {}).items():
            if not attrs.get("logging"):
                findings.append(
                    _make_finding(
                        "S3-005",
                        "LOW",
                        name,
                        "aws_s3_bucket",
                        scan_job_id,
                        "logging not configured",
                    )
                )

    # SG-001: SSH (port 22) open to 0.0.0.0/0
    if "SG-001" in rule_ids:
        for name, attrs in resources.get("aws_security_group", {}).items():
            for ingress in _ingress_rules(attrs):
                if _port_in_range(22, ingress) and _open_cidr(ingress):
                    findings.append(
                        _make_finding(
                            "SG-001",
                            "CRITICAL",
                            name,
                            "aws_security_group",
                            scan_job_id,
                            'from_port = 22, cidr_blocks = ["0.0.0.0/0"]',
                        )
                    )
                    break

    # SG-002: RDP (port 3389) open to 0.0.0.0/0
    if "SG-002" in rule_ids:
        for name, attrs in resources.get("aws_security_group", {}).items():
            for ingress in _ingress_rules(attrs):
                if _port_in_range(3389, ingress) and _open_cidr(ingress):
                    findings.append(
                        _make_finding(
                            "SG-002",
                            "CRITICAL",
                            name,
                            "aws_security_group",
                            scan_job_id,
                            'from_port = 3389, cidr_blocks = ["0.0.0.0/0"]',
                        )
                    )
                    break

    # SG-003: All ports open (protocol=-1 or from_port=0, to_port=65535) to 0.0.0.0/0
    if "SG-003" in rule_ids:
        for name, attrs in resources.get("aws_security_group", {}).items():
            for ingress in _ingress_rules(attrs):
                protocol = str(_first(ingress.get("protocol", "tcp")))
                from_p = int(_first(ingress.get("from_port", 1)) or 1)
                to_p = int(_first(ingress.get("to_port", 1)) or 1)
                if (
                    (protocol == "-1" or (from_p == 0 and to_p == 65535))
                    and _open_cidr(ingress)
                ):
                    findings.append(
                        _make_finding(
                            "SG-003",
                            "CRITICAL",
                            name,
                            "aws_security_group",
                            scan_job_id,
                            "all ports open to 0.0.0.0/0",
                        )
                    )
                    break

    # SG-004: HTTP (port 80) open to 0.0.0.0/0 (non-LB)
    if "SG-004" in rule_ids:
        for name, attrs in resources.get("aws_security_group", {}).items():
            for ingress in _ingress_rules(attrs):
                if _port_in_range(80, ingress) and _open_cidr(ingress):
                    findings.append(
                        _make_finding(
                            "SG-004",
                            "MEDIUM",
                            name,
                            "aws_security_group",
                            scan_job_id,
                            'from_port = 80, cidr_blocks = ["0.0.0.0/0"]',
                        )
                    )
                    break

    # IAM-001: Wildcard action in IAM policy
    if "IAM-001" in rule_ids:
        for res_type in ("aws_iam_policy", "aws_iam_role_policy", "aws_iam_user_policy"):
            for name, attrs in resources.get(res_type, {}).items():
                policy_str = str(_first(attrs.get("policy", "{}")))
                if (
                    '"Action": "*"' in policy_str
                    or '"Action":"*"' in policy_str
                    or '"action": "*"' in policy_str
                ):
                    findings.append(
                        _make_finding(
                            "IAM-001",
                            "HIGH",
                            name,
                            res_type,
                            scan_job_id,
                            '"Action": "*"',
                        )
                    )

    # IAM-002: Wildcard resource in IAM policy
    if "IAM-002" in rule_ids:
        for res_type in ("aws_iam_policy", "aws_iam_role_policy", "aws_iam_user_policy"):
            for name, attrs in resources.get(res_type, {}).items():
                policy_str = str(_first(attrs.get("policy", "{}")))
                if (
                    '"Resource": "*"' in policy_str
                    or '"Resource":"*"' in policy_str
                    or '"resource": "*"' in policy_str
                ):
                    findings.append(
                        _make_finding(
                            "IAM-002",
                            "HIGH",
                            name,
                            res_type,
                            scan_job_id,
                            '"Resource": "*"',
                        )
                    )

    # IAM-003: Root account usage (aws_iam_user, Principal=root)
    if "IAM-003" in rule_ids:
        for res_type in ("aws_iam_user", "aws_iam_role_policy"):
            for name, attrs in resources.get(res_type, {}).items():
                if res_type == "aws_iam_user" and name == "root":
                    findings.append(
                        _make_finding(
                            "IAM-003",
                            "CRITICAL",
                            name,
                            res_type,
                            scan_job_id,
                            "root user resource",
                        )
                    )

    # IAM-004: MFA not required (no require_mfa condition in policy)
    # Simplified: flag if role/policy doesn't mention mfa
    if "IAM-004" in rule_ids:
        for res_type in ("aws_iam_role_policy", "aws_iam_policy"):
            for name, attrs in resources.get(res_type, {}).items():
                policy_str = str(_first(attrs.get("policy", "{}")))
                if "mfa" not in policy_str.lower():
                    findings.append(
                        _make_finding(
                            "IAM-004",
                            "HIGH",
                            name,
                            res_type,
                            scan_job_id,
                            "MFA not required",
                        )
                    )

    # IAM-005: Inline policy used
    if "IAM-005" in rule_ids:
        for res_type in ("aws_iam_user_policy", "aws_iam_role_policy", "aws_iam_group_policy"):
            for name, attrs in resources.get(res_type, {}).items():
                findings.append(
                    _make_finding(
                        "IAM-005",
                        "LOW",
                        name,
                        res_type,
                        scan_job_id,
                        "inline policy (not managed policy)",
                    )
                )

    # ENC-001: EBS volume unencrypted
    if "ENC-001" in rule_ids:
        for name, attrs in resources.get("aws_ebs_volume", {}).items():
            encrypted = _first(attrs.get("encrypted", False))
            if not encrypted:
                findings.append(
                    _make_finding(
                        "ENC-001",
                        "HIGH",
                        name,
                        "aws_ebs_volume",
                        scan_job_id,
                        "encrypted = false",
                    )
                )

    # ENC-002: RDS encryption disabled
    if "ENC-002" in rule_ids:
        for name, attrs in resources.get("aws_db_instance", {}).items():
            encrypted = _first(attrs.get("storage_encrypted", False))
            if not encrypted:
                findings.append(
                    _make_finding(
                        "ENC-002",
                        "HIGH",
                        name,
                        "aws_db_instance",
                        scan_job_id,
                        "storage_encrypted = false",
                    )
                )

    # ENC-003: Secrets in plaintext (aws_secretsmanager_secret without recovery_window_in_days)
    if "ENC-003" in rule_ids:
        for name, attrs in resources.get("aws_secretsmanager_secret", {}).items():
            if not attrs.get("recovery_window_in_days"):
                findings.append(
                    _make_finding(
                        "ENC-003",
                        "CRITICAL",
                        name,
                        "aws_secretsmanager_secret",
                        scan_job_id,
                        "no recovery window",
                    )
                )

    # LOG-001: CloudTrail disabled
    if "LOG-001" in rule_ids:
        for name, attrs in resources.get("aws_cloudtrail", {}).items():
            enabled = _first(attrs.get("enable_logging", True))
            if not enabled:
                findings.append(
                    _make_finding(
                        "LOG-001",
                        "HIGH",
                        name,
                        "aws_cloudtrail",
                        scan_job_id,
                        "enable_logging = false",
                    )
                )

    # LOG-002: VPC Flow Logs disabled
    if "LOG-002" in rule_ids:
        for name, attrs in resources.get("aws_flow_log", {}).items():
            enabled = _first(attrs.get("enabled", True))
            if not enabled:
                findings.append(
                    _make_finding(
                        "LOG-002",
                        "MEDIUM",
                        name,
                        "aws_flow_log",
                        scan_job_id,
                        "enabled = false",
                    )
                )

    # LOG-003: S3 access logging disabled
    if "LOG-003" in rule_ids:
        for name, attrs in resources.get("aws_s3_bucket", {}).items():
            if not attrs.get("logging"):
                findings.append(
                    _make_finding(
                        "LOG-003",
                        "LOW",
                        name,
                        "aws_s3_bucket",
                        scan_job_id,
                        "logging not configured",
                    )
                )

    return findings


def _apply_cloudformation_rules(
    resources: Dict[str, List[Dict[str, Any]]], rules: List[Dict[str, Any]], scan_job_id: str
) -> List[Finding]:
    """
    Apply CloudFormation-specific security rules.
    Returns list of Finding objects for violations detected.
    """
    findings = []
    rule_ids = {r["rule_id"] for r in rules if r.get("enabled", False)}

    # S3-001: Public S3 Bucket ACL
    if "S3-001" in rule_ids:
        for resource in resources.get("AWS::S3::Bucket", []):
            acl = resource.get("Properties", {}).get("AccessControl")
            if acl in ("PublicRead", "PublicReadWrite", "AuthenticatedRead"):
                findings.append(
                    _make_finding(
                        "S3-001",
                        "CRITICAL",
                        resource.get("Name", "unknown"),
                        "AWS::S3::Bucket",
                        scan_job_id,
                        f"AccessControl: {acl}",
                    )
                )

    # S3-002: Public S3 Bucket Policy
    if "S3-002" in rule_ids:
        for resource in resources.get("AWS::S3::BucketPolicy", []):
            policy = str(resource.get("Properties", {}).get("PolicyText", ""))
            if '"Principal": "*"' in policy or '"Principal":"*"' in policy:
                findings.append(
                    _make_finding(
                        "S3-002",
                        "CRITICAL",
                        resource.get("Name", "unknown"),
                        "AWS::S3::BucketPolicy",
                        scan_job_id,
                        "Public principal in policy",
                    )
                )

    # S3-003: S3 Versioning disabled
    if "S3-003" in rule_ids:
        for resource in resources.get("AWS::S3::Bucket", []):
            versioning = resource.get("Properties", {}).get("VersioningConfiguration", {})
            status = versioning.get("Status", "Suspended")
            if status != "Enabled":
                findings.append(
                    _make_finding(
                        "S3-003",
                        "MEDIUM",
                        resource.get("Name", "unknown"),
                        "AWS::S3::Bucket",
                        scan_job_id,
                        f"VersioningConfiguration Status: {status}",
                    )
                )

    # S3-004: S3 Encryption disabled
    if "S3-004" in rule_ids:
        for resource in resources.get("AWS::S3::Bucket", []):
            if not resource.get("Properties", {}).get("BucketEncryption"):
                findings.append(
                    _make_finding(
                        "S3-004",
                        "HIGH",
                        resource.get("Name", "unknown"),
                        "AWS::S3::Bucket",
                        scan_job_id,
                        "BucketEncryption not configured",
                    )
                )

    # S3-005: S3 Logging disabled
    if "S3-005" in rule_ids:
        for resource in resources.get("AWS::S3::Bucket", []):
            if not resource.get("Properties", {}).get("LoggingConfiguration"):
                findings.append(
                    _make_finding(
                        "S3-005",
                        "LOW",
                        resource.get("Name", "unknown"),
                        "AWS::S3::Bucket",
                        scan_job_id,
                        "LoggingConfiguration not configured",
                    )
                )

    # SG-001: SSH (port 22) open to 0.0.0.0/0
    if "SG-001" in rule_ids:
        for resource in resources.get("AWS::EC2::SecurityGroup", []):
            for ingress in resource.get("Properties", {}).get("SecurityGroupIngress", []):
                if (
                    _cfn_port_in_range(22, ingress)
                    and _cfn_open_cidr(ingress)
                ):
                    findings.append(
                        _make_finding(
                            "SG-001",
                            "CRITICAL",
                            resource.get("Name", "unknown"),
                            "AWS::EC2::SecurityGroup",
                            scan_job_id,
                            "FromPort: 22, CidrIp: 0.0.0.0/0",
                        )
                    )
                    break

    # SG-002: RDP (port 3389) open to 0.0.0.0/0
    if "SG-002" in rule_ids:
        for resource in resources.get("AWS::EC2::SecurityGroup", []):
            for ingress in resource.get("Properties", {}).get("SecurityGroupIngress", []):
                if (
                    _cfn_port_in_range(3389, ingress)
                    and _cfn_open_cidr(ingress)
                ):
                    findings.append(
                        _make_finding(
                            "SG-002",
                            "CRITICAL",
                            resource.get("Name", "unknown"),
                            "AWS::EC2::SecurityGroup",
                            scan_job_id,
                            "FromPort: 3389, CidrIp: 0.0.0.0/0",
                        )
                    )
                    break

    # SG-003: All ports open to 0.0.0.0/0
    if "SG-003" in rule_ids:
        for resource in resources.get("AWS::EC2::SecurityGroup", []):
            for ingress in resource.get("Properties", {}).get("SecurityGroupIngress", []):
                proto = str(ingress.get("IpProtocol", "tcp"))
                from_p = ingress.get("FromPort", 1)
                to_p = ingress.get("ToPort", 1)
                if (
                    (proto == "-1" or (from_p == 0 and to_p == 65535))
                    and _cfn_open_cidr(ingress)
                ):
                    findings.append(
                        _make_finding(
                            "SG-003",
                            "CRITICAL",
                            resource.get("Name", "unknown"),
                            "AWS::EC2::SecurityGroup",
                            scan_job_id,
                            "All ports open to 0.0.0.0/0",
                        )
                    )
                    break

    # IAM-001: Wildcard action in IAM policy
    if "IAM-001" in rule_ids:
        for res_type in ("AWS::IAM::Policy", "AWS::IAM::ManagedPolicy", "AWS::IAM::RolePolicy"):
            for resource in resources.get(res_type, []):
                policy = str(
                    resource.get("Properties", {}).get("PolicyDocument", {}).get("Statement", [])
                )
                if '"Action": "*"' in policy or '"Action":"*"' in policy:
                    findings.append(
                        _make_finding(
                            "IAM-001",
                            "HIGH",
                            resource.get("Name", "unknown"),
                            res_type,
                            scan_job_id,
                            '"Action": "*"',
                        )
                    )

    # IAM-002: Wildcard resource in IAM policy
    if "IAM-002" in rule_ids:
        for res_type in ("AWS::IAM::Policy", "AWS::IAM::ManagedPolicy", "AWS::IAM::RolePolicy"):
            for resource in resources.get(res_type, []):
                policy = str(
                    resource.get("Properties", {}).get("PolicyDocument", {}).get("Statement", [])
                )
                if '"Resource": "*"' in policy or '"Resource":"*"' in policy:
                    findings.append(
                        _make_finding(
                            "IAM-002",
                            "HIGH",
                            resource.get("Name", "unknown"),
                            res_type,
                            scan_job_id,
                            '"Resource": "*"',
                        )
                    )

    # ENC-001: EBS volume unencrypted
    if "ENC-001" in rule_ids:
        for resource in resources.get("AWS::EC2::Volume", []):
            encrypted = resource.get("Properties", {}).get("Encrypted", False)
            if not encrypted:
                findings.append(
                    _make_finding(
                        "ENC-001",
                        "HIGH",
                        resource.get("Name", "unknown"),
                        "AWS::EC2::Volume",
                        scan_job_id,
                        "Encrypted: false",
                    )
                )

    # ENC-002: RDS encryption disabled
    if "ENC-002" in rule_ids:
        for resource in resources.get("AWS::RDS::DBInstance", []):
            encrypted = resource.get("Properties", {}).get("StorageEncrypted", False)
            if not encrypted:
                findings.append(
                    _make_finding(
                        "ENC-002",
                        "HIGH",
                        resource.get("Name", "unknown"),
                        "AWS::RDS::DBInstance",
                        scan_job_id,
                        "StorageEncrypted: false",
                    )
                )

    # LOG-001: CloudTrail disabled
    if "LOG-001" in rule_ids:
        for resource in resources.get("AWS::CloudTrail::Trail", []):
            logging_enabled = resource.get("Properties", {}).get("IsLogging", True)
            if not logging_enabled:
                findings.append(
                    _make_finding(
                        "LOG-001",
                        "HIGH",
                        resource.get("Name", "unknown"),
                        "AWS::CloudTrail::Trail",
                        scan_job_id,
                        "IsLogging: false",
                    )
                )

    return findings


# Helper functions


def _make_finding(
    rule_id: str,
    severity: str,
    resource_name: str,
    resource_type: str,
    scan_job_id: str,
    code_snippet: str = "",
) -> Finding:
    """Create a Finding object with standard parameters."""
    return Finding(
        rule_id=rule_id,
        severity=severity,
        resource_name=resource_name,
        resource_type=resource_type,
        scan_job_id=scan_job_id,
        code_snippet=code_snippet[:500],  # Cap at 500 chars per schema
    )


def _first(val: Any) -> Any:
    """
    python-hcl2 wraps values in lists; unwrap the first element.
    Returns None if empty or non-list non-None value.
    """
    if isinstance(val, list):
        return val[0] if val else None
    return val


def _ingress_rules(attrs: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract ingress rules from Terraform security group attributes."""
    rules = attrs.get("ingress", [])
    if isinstance(rules, dict):
        return [rules]
    return rules if isinstance(rules, list) else []


def _port_in_range(port: int, ingress: Dict[str, Any]) -> bool:
    """Check if a port falls within the from_port to to_port range."""
    from_p = int(_first(ingress.get("from_port", 0)) or 0)
    to_p = int(_first(ingress.get("to_port", 0)) or 0)
    return from_p <= port <= to_p


def _open_cidr(ingress: Dict[str, Any]) -> bool:
    """Check if ingress rule allows 0.0.0.0/0 or ::/0."""
    cidrs = _first(ingress.get("cidr_blocks", []))
    if isinstance(cidrs, list):
        return "0.0.0.0/0" in cidrs or "::/0" in cidrs
    return cidrs in ("0.0.0.0/0", "::/0")


def _cfn_port_in_range(port: int, ingress: Dict[str, Any]) -> bool:
    """Check if a port falls within CFN FromPort/ToPort range."""
    from_p = ingress.get("FromPort", 0)
    to_p = ingress.get("ToPort", 0)
    return from_p <= port <= to_p


def _cfn_open_cidr(ingress: Dict[str, Any]) -> bool:
    """Check if CFN ingress rule allows 0.0.0.0/0 or ::/0."""
    cidr = ingress.get("CidrIp", "")
    return cidr in ("0.0.0.0/0", "::/0")


def _update_scan_status(scan_job_id: str, status: str) -> None:
    """Update scan-jobs table: set status and updated_at timestamp."""
    table = dynamodb.Table(SCAN_JOBS_TABLE)
    # Query first to get created_at (sort key needed for update)
    response = table.query(KeyConditionExpression=DdbKey("scan_job_id").eq(scan_job_id))
    if response.get("Items"):
        item = response["Items"][0]
        created_at = item.get("created_at")
        table.update_item(
            Key={"scan_job_id": scan_job_id, "created_at": created_at},
            UpdateExpression="SET #s = :s, updated_at = :t",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": status,
                ":t": datetime.now(timezone.utc).isoformat(),
            },
        )
