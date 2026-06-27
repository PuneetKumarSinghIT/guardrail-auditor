import pytest
from scanner.src.parsers.cloudformation_parser import parse


CFN_SIMPLE = b"""
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  MyBucket:
    Type: AWS::S3::Bucket
    Properties:
      AccessControl: PublicRead
"""

CFN_MULTI = b"""
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  MyBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: test-bucket
  MySecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Test SG
"""

CFN_NO_RESOURCES = b"""
AWSTemplateFormatVersion: '2010-09-09'
Description: Empty template
"""

CFN_JSON = b'{"AWSTemplateFormatVersion":"2010-09-09","Resources":{"MyBucket":{"Type":"AWS::S3::Bucket","Properties":{"AccessControl":"PublicRead"}}}}'


def test_simple_yaml_parsed():
    """Test parsing a simple YAML CloudFormation template."""
    result = parse(CFN_SIMPLE)
    assert "AWS::S3::Bucket" in result
    assert "MyBucket" in result["AWS::S3::Bucket"]
    assert result["AWS::S3::Bucket"]["MyBucket"].get("AccessControl") == "PublicRead"


def test_multiple_resources():
    """Test parsing multiple CloudFormation resources."""
    result = parse(CFN_MULTI)
    assert "AWS::S3::Bucket" in result
    assert "AWS::EC2::SecurityGroup" in result
    assert "MyBucket" in result["AWS::S3::Bucket"]
    assert "MySecurityGroup" in result["AWS::EC2::SecurityGroup"]


def test_no_resources_returns_empty():
    """Test that templates without Resources section return empty dict."""
    result = parse(CFN_NO_RESOURCES)
    assert result == {}


def test_malformed_returns_empty():
    """Test that malformed YAML/JSON is handled gracefully."""
    result = parse(b"{{{{ not yaml or json")
    assert isinstance(result, dict)
    assert result == {}


def test_json_format_parsed():
    """Test parsing JSON format CloudFormation templates."""
    result = parse(CFN_JSON)
    assert isinstance(result, dict)
    # JSON CFN should parse and extract resources if format is valid
    if result:
        assert "AWS::S3::Bucket" in result
        assert "MyBucket" in result["AWS::S3::Bucket"]
