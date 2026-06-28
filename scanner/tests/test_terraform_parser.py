import pytest
from scanner.src.parsers.terraform_parser import parse


def test_valid_tf_single_resource():
    """Test parsing a single Terraform resource."""
    content = b'''
resource "aws_s3_bucket" "my_bucket" {
  bucket = "my-test-bucket"
  acl    = "public-read"
}
'''
    result = parse(content)
    # hcl2 parser preserves quotes in keys
    assert '"aws_s3_bucket"' in result
    assert '"my_bucket"' in result['"aws_s3_bucket"']
    assert isinstance(result['"aws_s3_bucket"']['"my_bucket"'], dict)


def test_valid_tf_multiple_resources():
    """Test parsing multiple resource types."""
    content = b'''
resource "aws_s3_bucket" "bucket1" {
  bucket = "bucket1"
}
resource "aws_security_group" "sg1" {
  name = "test-sg"
}
'''
    result = parse(content)
    assert '"aws_s3_bucket"' in result
    assert '"aws_security_group"' in result
    assert '"bucket1"' in result['"aws_s3_bucket"']
    assert '"sg1"' in result['"aws_security_group"']


def test_empty_content_returns_empty():
    """Test that empty content returns empty dict."""
    result = parse(b"")
    assert result == {}


def test_malformed_hcl_returns_empty():
    """Test that malformed HCL is handled gracefully."""
    result = parse(b"this is not valid hcl {{{")
    assert isinstance(result, dict)
    assert result == {}


def test_nested_blocks_preserved():
    """Test that nested blocks in resources are preserved."""
    content = b'''
resource "aws_s3_bucket" "secure_bucket" {
  bucket = "secure"
  versioning {
    enabled = true
  }
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
}
'''
    result = parse(content)
    assert '"aws_s3_bucket"' in result
    assert '"secure_bucket"' in result['"aws_s3_bucket"']
    attrs = result['"aws_s3_bucket"']['"secure_bucket"']
    # Nested blocks should be present in attrs dict
    assert isinstance(attrs, dict)
    assert "versioning" in attrs or "server_side_encryption_configuration" in attrs
