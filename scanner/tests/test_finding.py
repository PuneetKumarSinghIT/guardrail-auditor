from scanner.src.models.finding import Finding


def _make_finding(**kwargs) -> Finding:
    defaults = dict(
        rule_id="S3-001",
        severity="CRITICAL",
        resource_name="aws_s3_bucket.public",
        resource_type="aws_s3_bucket",
        scan_job_id="job-abc-123",
    )
    defaults.update(kwargs)
    return Finding(**defaults)


def test_finding_defaults():
    f = _make_finding()
    assert f.line_number == 0
    assert f.code_snippet == ""
    assert f.ai_explanation == ""
    assert f.ai_fix_code == ""
    assert f.dismissed is False
    assert f.dismissed_at is None
    assert len(f.finding_id) == 36  # UUID v4 format


def test_to_dynamodb_item_basic():
    f = _make_finding(line_number=10, code_snippet="resource {}")
    item = f.to_dynamodb_item()
    assert item["scan_job_id"] == "job-abc-123"
    assert item["rule_id"] == "S3-001"
    assert item["severity"] == "CRITICAL"
    assert item["resource_name"] == "aws_s3_bucket.public"
    assert item["line_number"] == 10
    assert item["code_snippet"] == "resource {}"
    assert item["dismissed"] is False
    assert "dismissed_at" not in item


def test_to_dynamodb_item_truncates_code_snippet():
    long_snippet = "x" * 600
    f = _make_finding(code_snippet=long_snippet)
    item = f.to_dynamodb_item()
    assert len(item["code_snippet"]) == 500


def test_to_dynamodb_item_includes_dismissed_at_when_set():
    f = _make_finding(dismissed=True, dismissed_at="2026-06-28T00:00:00Z")
    item = f.to_dynamodb_item()
    assert item["dismissed"] is True
    assert item["dismissed_at"] == "2026-06-28T00:00:00Z"


def test_from_dynamodb_item_round_trips():
    original = _make_finding(line_number=5, code_snippet="bad = true")
    item = original.to_dynamodb_item()
    restored = Finding.from_dynamodb_item(item)
    assert restored.rule_id == original.rule_id
    assert restored.severity == original.severity
    assert restored.resource_name == original.resource_name
    assert restored.line_number == 5
    assert restored.code_snippet == "bad = true"
    assert restored.dismissed is False
