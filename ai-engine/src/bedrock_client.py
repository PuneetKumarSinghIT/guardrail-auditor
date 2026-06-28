"""Amazon Bedrock runtime wrapper for the AI analysis engine.

Thin boto3 wrapper around bedrock-runtime invoke_model using the Anthropic
Messages API on Bedrock. Two convenience methods route to the right model:

    explain_risk(prompt)  -> Haiku  (cheap, high volume, 300 token cap)
    generate_fix(prompt)  -> Sonnet (precision for valid IaC, 800 token cap)

Retries ThrottlingException with exponential backoff (max 3). The client is
injectable for testing — pass a stub client and a no-op sleeper.

Model IDs come from env (BEDROCK_EXPLAIN_MODEL / BEDROCK_FIX_MODEL) so CDK can
inject them; defaults match the project's locked model choices.
"""
import json
import logging
import os
import time

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Claude 4.x on Bedrock is inference-profile-only — invoke via the us.* cross-region
# profile IDs, not the bare foundation-model IDs. CDK injects these; defaults match.
EXPLAIN_MODEL = os.environ.get(
    "BEDROCK_EXPLAIN_MODEL", "us.anthropic.claude-haiku-4-5-20251001-v1:0"
)
FIX_MODEL = os.environ.get("BEDROCK_FIX_MODEL", "us.anthropic.claude-sonnet-4-6")

EXPLAIN_MAX_TOKENS = 300
FIX_MAX_TOKENS = 800
MAX_RETRIES = 3
ANTHROPIC_VERSION = "bedrock-2023-05-31"

_THROTTLE_CODES = ("ThrottlingException", "TooManyRequestsException")


class BedrockClient:
    """Bedrock-runtime wrapper with model routing and throttle retry."""

    def __init__(self, client=None, max_retries: int = MAX_RETRIES, sleeper=time.sleep):
        self._client = client if client is not None else boto3.client("bedrock-runtime")
        self._max_retries = max_retries
        self._sleep = sleeper

    def invoke_model(self, model_id: str, prompt: str, max_tokens: int) -> str:
        """Invoke a Bedrock Anthropic model, returning the assistant text.

        Retries throttling with exponential backoff up to max_retries.
        """
        body = json.dumps(
            {
                "anthropic_version": ANTHROPIC_VERSION,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": prompt}]}
                ],
            }
        )

        attempt = 0
        while True:
            try:
                response = self._client.invoke_model(modelId=model_id, body=body)
                payload = json.loads(response["body"].read())
                return self._extract_text(payload)
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                if code in _THROTTLE_CODES and attempt < self._max_retries:
                    delay = 2 ** attempt
                    logger.warning(
                        json.dumps(
                            {
                                "event": "bedrock_throttled_retry",
                                "model_id": model_id,
                                "attempt": attempt + 1,
                                "delay_s": delay,
                            }
                        )
                    )
                    self._sleep(delay)
                    attempt += 1
                    continue
                logger.error(
                    json.dumps(
                        {
                            "event": "bedrock_invoke_failed",
                            "model_id": model_id,
                            "error_code": code,
                        }
                    )
                )
                raise

    @staticmethod
    def _extract_text(payload: dict) -> str:
        """Pull the first text block out of an Anthropic Messages response."""
        for block in payload.get("content", []):
            if block.get("type") == "text":
                return block.get("text", "").strip()
        return ""

    def explain_risk(self, prompt: str) -> str:
        """Route to the explanation model (Haiku) with the explain token cap."""
        return self.invoke_model(EXPLAIN_MODEL, prompt, EXPLAIN_MAX_TOKENS)

    def generate_fix(self, prompt: str) -> str:
        """Route to the fix model (Sonnet) with the fix token cap."""
        return self.invoke_model(FIX_MODEL, prompt, FIX_MAX_TOKENS)
