# INTENTIONALLY MISCONFIGURED — DO NOT FIX
# PRIMARY DEMO FILE — Use this for client demos. One upload triggers ALL CRITICAL rules.
# Triggers: S3-001, S3-002, S3-004, SG-001, SG-002, SG-003, IAM-001, IAM-002,
#           IAM-003, ENC-001, ENC-002, ENC-003, LOG-001, LOG-002
# Checkov expected failures: CKV_AWS_3, CKV_AWS_16, CKV_AWS_18, CKV_AWS_19,
#   CKV_AWS_20, CKV_AWS_24, CKV_AWS_25, CKV_AWS_40, CKV_AWS_53-56, CKV_AWS_274

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ─── S3 VIOLATIONS ────────────────────────────────────────────────────────────

# S3-001, S3-002, S3-004, S3-005: Public bucket with no encryption or logging
resource "aws_s3_bucket" "demo_public_bucket" {
  bucket = "demo-master-bad-public-bucket-12345"
}

resource "aws_s3_bucket_ownership_controls" "demo" {
  bucket = aws_s3_bucket.demo_public_bucket.id
  rule { object_ownership = "BucketOwnerPreferred" }
}

resource "aws_s3_bucket_acl" "demo_public_acl" {
  bucket     = aws_s3_bucket.demo_public_bucket.id
  acl        = "public-read"
  depends_on = [aws_s3_bucket_ownership_controls.demo]
}

resource "aws_s3_bucket_public_access_block" "demo_disabled" {
  bucket                  = aws_s3_bucket.demo_public_bucket.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "demo_public_policy" {
  bucket = aws_s3_bucket.demo_public_bucket.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicRead"
      Effect    = "Allow"
      Principal = "*"
      Action    = ["s3:GetObject", "s3:ListBucket"]
      Resource  = [aws_s3_bucket.demo_public_bucket.arn, "${aws_s3_bucket.demo_public_bucket.arn}/*"]
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.demo_disabled]
}

# ─── NETWORK VIOLATIONS ───────────────────────────────────────────────────────

# SG-001, SG-002, SG-003: Security group open to the entire internet on every port
resource "aws_security_group" "demo_open_sg" {
  name        = "demo-master-bad-open-sg"
  description = "Demo: all ports open to the internet"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH open to world - SG-001"
  }

  ingress {
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "RDP open to world - SG-002"
  }

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All traffic - SG-003"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ─── IAM VIOLATIONS ───────────────────────────────────────────────────────────

# IAM-001, IAM-002, IAM-003, IAM-005: Wildcard permissions + inline policy + root trust
resource "aws_iam_role" "demo_insecure_role" {
  name = "demo-master-bad-insecure-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::*:root" }
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "demo_wildcard_inline" {
  name = "demo-wildcard-inline"
  role = aws_iam_role.demo_insecure_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "*"
      Resource = "*"
    }]
  })
}

# ─── ENCRYPTION VIOLATIONS ────────────────────────────────────────────────────

# ENC-001: EBS volume explicitly unencrypted
resource "aws_ebs_volume" "demo_unencrypted" {
  availability_zone = "us-east-1a"
  size              = 50
  encrypted         = false
}

# ENC-002 + ENC-003: RDS with no encryption AND hardcoded password in plaintext
resource "aws_db_instance" "demo_insecure_db" {
  identifier          = "demo-master-bad-db"
  engine              = "mysql"
  engine_version      = "8.0"
  instance_class      = "db.t3.micro"
  db_name             = "appdb"
  username            = "root"
  password            = "P@ssw0rd123!"
  allocated_storage   = 20
  storage_encrypted   = false
  publicly_accessible = true
  skip_final_snapshot = true
}

# ─── LOGGING VIOLATIONS ───────────────────────────────────────────────────────

# LOG-001: CloudTrail explicitly disabled — no API audit trail
resource "aws_cloudtrail" "demo_disabled_trail" {
  name                          = "demo-master-bad-trail"
  s3_bucket_name                = aws_s3_bucket.demo_public_bucket.id
  include_global_service_events = false
  is_multi_region_trail         = false
  enable_logging                = false

  depends_on = [aws_s3_bucket_policy.demo_public_policy]
}

# LOG-002: VPC with no flow logs attached
resource "aws_vpc" "demo_no_flow_logs" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true

  tags = {
    Name = "demo-master-bad-vpc-no-flow-logs"
  }
}
