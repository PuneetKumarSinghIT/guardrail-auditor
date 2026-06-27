terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Compliant IAM role: scoped actions, no wildcards, managed policy (not inline)
resource "aws_iam_role" "secure_lambda_role" {
  name        = "guardrail-secure-lambda-role"
  description = "Least-privilege role for guardrail scanner Lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

# Managed policy with specific actions on specific resources — no wildcards
resource "aws_iam_policy" "secure_lambda_policy" {
  name        = "guardrail-secure-lambda-policy"
  description = "Scoped permissions for the scanner Lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DynamoDBScanJobsAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ]
        Resource = "arn:aws:dynamodb:us-east-1:*:table/scan-jobs"
      },
      {
        Sid    = "S3UploadBucketReadAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion"
        ]
        Resource = "arn:aws:s3:::guardrail-iac-uploads-*/*"
      },
      {
        Sid    = "CloudWatchLogsWrite"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:us-east-1:*:log-group:/guardrail/*"
      }
    ]
  })
}

# Attach managed policy to role — never use inline policies
resource "aws_iam_role_policy_attachment" "secure_lambda" {
  role       = aws_iam_role.secure_lambda_role.name
  policy_arn = aws_iam_policy.secure_lambda_policy.arn
}
