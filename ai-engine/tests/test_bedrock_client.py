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
