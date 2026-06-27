# INTENTIONALLY MISCONFIGURED — DO NOT FIX
# Triggers: SG-001 (SSH open to world), SG-002 (RDP open to world), SG-003 (All traffic open)
# Used as a scanner demo target. Checkov checks: CKV_AWS_25, CKV_AWS_24, CKV_AWS_277

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# SG-001, SG-002, SG-003: Wide-open security group — all common attack vectors exposed
resource "aws_security_group" "open_all_sg" {
  name        = "demo-open-all-insecure-sg"
  description = "Intentionally insecure security group for demo scanning"

  # SG-001: SSH open to the entire internet — brute force attack vector
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH from anywhere - INSECURE"
  }

  # SG-002: RDP open to the entire internet — Windows remote exploit vector
  ingress {
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "RDP from anywhere - INSECURE"
  }

  # SG-004: HTTP open on a non-LB resource
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP from anywhere on application server - INSECURE"
  }

  # SG-003: All traffic open — complete exposure, makes all other rules irrelevant
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All traffic from anywhere - CRITICAL MISCONFIGURATION"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
