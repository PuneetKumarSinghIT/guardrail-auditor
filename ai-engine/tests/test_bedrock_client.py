import io
import json
import os
from unittest.mock import MagicMock

from botocore.exceptions import ClientError

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("BEDROCK_EXPLAIN_MODEL", "anthropic.claude-haiku-4-5-20251001")
os.environ.setdefault("BEDROCK_FIX_MODEL", "anthropic.claude-sonnet-4-6")

from src import bedrock_client as bc
from src.bedrock_client import BedrockClient


def _bedrock_response(text: str) -> dict:
    """Mimic a bedrock-runtime invoke_model response (body is a StreamingBody)."""
    payload = {"content": [{"type": "text", "text": text}]}
    return {"body": io.BytesIO(json.dumps(payload).encode("utf-8"))}


def _throttle_error() -> ClientError:
    return ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "slow down"}},
        "InvokeModel",
    )


def test_invoke_model_returns_text():
    fake = MagicMock()
    fake.invoke_model.return_value = _bedrock_response("This bucket is public.")
    client = BedrockClient(client=fake)

    result = client.invoke_model("some-model", "prompt", 300)

    assert result == "This bucket is public."
    fake.invoke_model.assert_called_once()


def test_throttling_is_retried_then_succeeds():
    fake = MagicMock()
    # First call throttles, second call succeeds
    fake.invoke_model.side_effect = [
        _throttle_error(),
        _bedrock_response("recovered"),
    ]
    sleeps = []
    client = BedrockClient(client=fake, sleeper=sleeps.append)

    result = client.invoke_model("some-model", "prompt", 300)

    assert result == "recovered"
    assert fake.invoke_model.call_count == 2
    assert sleeps == [1]  # 2 ** 0 backoff before the single retry


def test_model_routing_uses_correct_model_per_method():
    fake = MagicMock()
    # Fresh response each call — a StreamingBody is single-read (exhausted after .read())
    fake.invoke_model.side_effect = lambda **kw: _bedrock_response("ok")
    client = BedrockClient(client=fake)

    client.explain_risk("explain this")
    explain_kwargs = fake.invoke_model.call_args.kwargs
    assert explain_kwargs["modelId"] == bc.EXPLAIN_MODEL
    assert json.loads(explain_kwargs["body"])["max_tokens"] == bc.EXPLAIN_MAX_TOKENS

    client.generate_fix("fix this")
    fix_kwargs = fake.invoke_model.call_args.kwargs
    assert fix_kwargs["modelId"] == bc.FIX_MODEL
    assert json.loads(fix_kwargs["body"])["max_tokens"] == bc.FIX_MAX_TOKENS


# ── openai_compat provider (gpt-oss via runtime bearer token) ────────────────

import base64


def test_token_generator_format_and_version_quirk():
    """Runtime token is base64 of a presigned CallWithBearerToken URL with Version=1
    appended (Version must be in the token but NOT in the signed canonical request)."""
    token = bc.generate_bedrock_bearer_token(region="us-east-1")
    assert token.startswith("bedrock-api-key-")
    decoded = base64.b64decode(token[len("bedrock-api-key-"):]).decode()
    assert decoded.startswith("bedrock.amazonaws.com/?Action=CallWithBearerToken")
    assert decoded.endswith("&Version=1")
    # Version is appended AFTER the signature params, never signed
    assert "X-Amz-Signature=" in decoded
    assert decoded.index("X-Amz-Signature=") < decoded.index("&Version=1")


def _openai_response(text: str) -> dict:
    return {"choices": [{"finish_reason": "stop", "message": {"content": text}}]}


def test_openai_compat_explain_returns_content():
    captured = {}

    def fake_post(url, headers, body, timeout=60):
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = body
        return _openai_response("This S3 bucket is world-readable.")

    client = BedrockClient(
        provider="openai_compat",
        http_post=fake_post,
        token_generator=lambda region=None: "bedrock-api-key-FAKE",
    )
    result = client.explain_risk("explain S3-001")

    assert result == "This S3 bucket is world-readable."
    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer bedrock-api-key-FAKE"
    assert captured["body"]["model"] == bc.OPENAI_EXPLAIN_MODEL


def test_openai_compat_routing_and_fresh_token_per_call():
    calls = []
    tokens = []

    def fake_post(url, headers, body, timeout=60):
        calls.append(body["model"])
        return _openai_response("ok")

    def fake_token(region=None):
        tokens.append(1)
        return "bedrock-api-key-FAKE"

    client = BedrockClient(
        provider="openai_compat", http_post=fake_post, token_generator=fake_token
    )
    client.explain_risk("e")
    client.generate_fix("f")

    assert calls == [bc.OPENAI_EXPLAIN_MODEL, bc.OPENAI_FIX_MODEL]
    assert len(tokens) == 2  # a fresh short-lived token is generated for every call


def test_openai_compat_reasoning_fallback_when_content_null():
    """gpt-oss may return content=null with the answer in `reasoning` — fall back to it."""
    def fake_post(url, headers, body, timeout=60):
        return {"choices": [{"message": {"content": None, "reasoning": "fallback answer"}}]}

    client = BedrockClient(
        provider="openai_compat",
        http_post=fake_post,
        token_generator=lambda region=None: "t",
    )
    assert client.explain_risk("x") == "fallback answer"
