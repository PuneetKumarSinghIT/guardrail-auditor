terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Compliant security group: no 0.0.0.0/0 on any sensitive port
resource "aws_security_group" "restricted_sg" {
  name        = "guardrail-restricted-sg"
  description = "Security group with locked-down ingress rules"
  vpc_id      = var.vpc_id

  # SSH only from known corporate CIDR — never 0.0.0.0/0
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
    description = "SSH from internal network only"
  }

  # HTTPS from anywhere is acceptable for a public web endpoint
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS public web traffic"
  }

  # Outbound: allow all (standard for most workloads)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }
}

variable "vpc_id" {
  description = "VPC ID where the security group will be created"
  type        = string
  default     = "vpc-00000000"
}
