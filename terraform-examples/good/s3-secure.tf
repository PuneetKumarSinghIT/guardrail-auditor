terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Logging bucket must exist before the main bucket references it
resource "aws_s3_bucket" "logging_bucket" {
  bucket = "guardrail-demo-access-logs"
}

resource "aws_s3_bucket_ownership_controls" "logging_bucket" {
  bucket = aws_s3_bucket.logging_bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

# Compliant S3 bucket: encrypted, versioned, no public access, access logging enabled
resource "aws_s3_bucket" "secure_bucket" {
  bucket = "guardrail-secure-demo-bucket"
}

resource "aws_s3_bucket_versioning" "secure" {
  bucket = aws_s3_bucket.secure_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "secure" {
  bucket = aws_s3_bucket.secure_bucket.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "secure" {
  bucket = aws_s3_bucket.secure_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_logging" "secure" {
  bucket        = aws_s3_bucket.secure_bucket.id
  target_bucket = aws_s3_bucket.logging_bucket.id
  target_prefix = "s3-access-logs/"
}

resource "aws_s3_bucket_lifecycle_configuration" "secure" {
  bucket = aws_s3_bucket.secure_bucket.id
  rule {
    id     = "expire-old-objects"
    status = "Enabled"
    expiration {
      days = 90
    }
  }
}
