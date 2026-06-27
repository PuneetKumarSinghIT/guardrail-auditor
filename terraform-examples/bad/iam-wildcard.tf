# INTENTIONALLY MISCONFIGURED — DO NOT FIX
# Triggers: IAM-001 (Wildcard Action), IAM-002 (Wildcard Resource), IAM-005 (Inline Policy)
# Used as a scanner demo target. Checkov checks: CKV_AWS_40, CKV_AWS_274, CKV_AWS_355

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# IAM-001, IAM-002: Role with wildcard action and wildcard resource — full account access
resource "aws_iam_role" "insecure_admin_role" {
  name        = "demo-insecure-wildcard-role"
  description = "Intentionally over-privileged role for demo scanning"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "ec2.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

# IAM-005: Inline policy (should be a separate aws_iam_policy resource)
# IAM-001: Action = "*" grants ALL AWS API actions
# IAM-002: Resource = "*" applies to EVERY resource in the account
resource "aws_iam_role_policy" "wildcard_inline_policy" {
  name = "demo-wildcard-inline-policy"
  role = aws_iam_role.insecure_admin_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "FullAccountAccess"
        Effect   = "Allow"
        Action   = "*"
        Resource = "*"
      }
    ]
  })
}

# IAM-002 additional: Managed policy also using wildcard resource
resource "aws_iam_policy" "insecure_wildcard_policy" {
  name        = "demo-insecure-wildcard-managed-policy"
  description = "Intentionally over-permissive managed policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "S3FullAccessAllBuckets"
        Effect   = "Allow"
        Action   = ["s3:*"]
        Resource = "*"
      },
      {
        Sid      = "DynamoFullAccessAllTables"
        Effect   = "Allow"
        Action   = ["dynamodb:*"]
        Resource = "*"
      }
    ]
  })
}
