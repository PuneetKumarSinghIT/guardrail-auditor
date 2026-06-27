# INTENTIONALLY MISCONFIGURED — DO NOT FIX
# Triggers: ENC-001 (EBS Unencrypted), ENC-002 (RDS Encryption Disabled), ENC-003 (Plaintext Secret)
# Used as a scanner demo target. Checkov checks: CKV_AWS_3, CKV_AWS_16, CKV_AWS_17

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ENC-001: EBS volume with encryption explicitly disabled
resource "aws_ebs_volume" "unencrypted_disk" {
  availability_zone = "us-east-1a"
  size              = 100
  encrypted         = false
  type              = "gp3"

  tags = {
    Name = "demo-unencrypted-ebs"
  }
}

# ENC-002: RDS instance with storage encryption disabled
# ENC-003: Hardcoded master password in plaintext (will end up in Terraform state)
resource "aws_db_instance" "unencrypted_db" {
  identifier        = "demo-insecure-db"
  engine            = "mysql"
  engine_version    = "8.0"
  instance_class    = "db.t3.micro"
  db_name           = "appdb"
  username          = "admin"
  password          = "SuperSecret123!"
  allocated_storage = 20

  storage_encrypted   = false
  skip_final_snapshot = true
  publicly_accessible = true

  tags = {
    Name = "demo-unencrypted-rds"
  }
}

# ENC-001 additional: EBS snapshot also unencrypted
resource "aws_ebs_snapshot_copy" "unencrypted_snapshot" {
  source_snapshot_id = "snap-00000000000000000"
  source_region      = "us-east-1"
  encrypted          = false

  tags = {
    Name = "demo-unencrypted-snapshot"
  }
}

# ENC-003: Secrets Manager secret with hardcoded value (should be rotated, not literal)
resource "aws_secretsmanager_secret_version" "plaintext_secret" {
  secret_id     = "demo/app/api-key"
  secret_string = "hardcoded-api-key-value-abc123xyz"
}
