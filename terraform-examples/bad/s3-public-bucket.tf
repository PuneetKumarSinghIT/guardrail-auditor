# INTENTIONALLY MISCONFIGURED — DO NOT FIX
# Triggers: S3-001 (Public ACL), S3-002 (Public Policy), S3-004 (No Encryption)
# Used as a scanner demo target. Checkov checks: CKV_AWS_19, CKV_AWS_20, CKV_AWS_53-56

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

resource "aws_s3_bucket" "insecure_bucket" {
  bucket = "demo-public-insecure-bucket-99999"
  # S3-003: No versioning configured
  # S3-004: No server-side encryption configured
  # S3-005: No access logging configured
}

# S3-001: Public read ACL — anyone on the internet can list and read objects
resource "aws_s3_bucket_acl" "insecure_acl" {
  bucket = aws_s3_bucket.insecure_bucket.id
  acl    = "public-read"

  depends_on = [aws_s3_bucket_ownership_controls.insecure]
}

resource "aws_s3_bucket_ownership_controls" "insecure" {
  bucket = aws_s3_bucket.insecure_bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

# S3-001 amplified: Public access block DISABLED — allows the public ACL above to take effect
resource "aws_s3_bucket_public_access_block" "insecure" {
  bucket = aws_s3_bucket.insecure_bucket.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# S3-002: Bucket policy with Principal '*' — unauthenticated public read
resource "aws_s3_bucket_policy" "public_policy" {
  bucket = aws_s3_bucket.insecure_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.insecure_bucket.arn,
          "${aws_s3_bucket.insecure_bucket.arn}/*"
        ]
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.insecure]
}
