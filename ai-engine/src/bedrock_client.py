"""Amazon Bedrock client for the AI analysis engine — two providers, one interface.

PROVIDER is selected by the BEDROCK_PROVIDER env var:

  "anthropic"     (default, durable target): boto3 bedrock-runtime invoke_model on the
                  Claude inference profiles (Haiku explain / Sonnet fix). Pure IAM auth,
                  no secrets. Works once the account's Bedrock model access is granted.

  "openai_compat" (works today on this account): calls the OpenAI-compatible Bedrock
                  endpoint for gpt-oss-120b. Auth is a SHORT-LIVED bearer token GENERATED
                  AT RUNTIME from the caller's own IAM credentials (SigV4-presigned
                  CallWithBearerToken) — never stored, never logged, regenerated per call,
                  discarded after use. No API key in code, Secrets Manager, env, or logs.

The two providers expose the same explain_risk()/generate_fix() surface so analyzer.py is
provider-agnostic — flipping BEDROCK_PROVIDER is the only change needed when Claude access lands.
"""
import base64
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request

import boto3
from botocore.auth import SigV4QueryAuth
from botocore.awsrequest import AWSRequest
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

PROVIDER = os.environ.get("BEDROCK_PROVIDER", "anthropic")  # "anthropic" | "openai_compat"
BEDROCK_REGION = os.environ.get("AWS_REGION", "us-east-1")

# ── anthropic provider (inference-profile IDs; Claude 4.x is profile-only) ───
EXPLAIN_MODEL = os.environ.get(
    "BEDROCK_EXPLAIN_MODEL", "us.anthropic.claude-haiku-4-5-20251001-v1:0"
)
FIX_MODEL = os.environ.get("BEDROCK_FIX_MODEL", "us.anthropic.claude-sonnet-4-6")
ANTHROPIC_VERSION = "bedrock-2023-05-31"
EXPLAIN_MAX_TOKENS = 300
FIX_MAX_TOKENS = 800

# ── openai_compat provider (gpt-oss via OpenAI-compatible Bedrock endpoint) ──
OPENAI_ENDPOINT = os.environ.get(
    "BEDROCK_OPENAI_ENDPOINT", "https://bedrock-mantle.us-east-1.api.aws/v1"
)
OPENAI_EXPLAIN_MODEL = os.environ.get("BEDROCK_OPENAI_EXPLAIN_MODEL", "openai.gpt-oss-120b")
OPENAI_FIX_MODEL = os.environ.get("BEDROCK_OPENAI_FIX_MODEL", "openai.gpt-oss-120b")
# gpt-oss is a reasoning model — give headroom beyond the visible answer
OPENAI_EXPLAIN_MAX_TOKENS = 1024
OPENAI_FIX_MAX_TOKENS = 2048
TOKEN_TTL_SECONDS = 900  # short-lived: generated per call, never persisted

MAX_RETRIES = 3
_THROTTLE_CODES = ("ThrottlingException", "TooManyRequestsException")


def generate_bedrock_bearer_token(region: str = None, ttl: int = TOKEN_TTL_SECONDS) -> str:
    """Generate a short-lived Bedrock bearer token from the caller's IAM credentials.

    SigV4-presigns a `CallWithBearerToken` request and base64-encodes it. The token is
    derived locally from the ambient role credentials — no network call, no stored secret.

    Quirk (verified against the service): `Version=1` must be present in the final token URL
    but EXCLUDED from the signed canonical request, so it is appended AFTER signing.
    """
    region = region or BEDROCK_REGION
    creds = boto3.Session().get_credentials().get_frozen_credentials()
    request = AWSRequest(
        method="POST", url="https://bedrock.amazonaws.com/?Action=CallWithBearerToken"
    )
    SigV4QueryAuth(creds, "bedrock", region, expires=ttl).add_auth(request)
    payload = request.url.split("://", 1)[1] + "&Version=1"
    return "bedrock-api-key-" + base64.b64encode(payload.encode("utf-8")).decode("utf-8")


def _http_post_json(url: str, headers: dict, body: dict, timeout: int = 60) -> dict:
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST", headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        return json.loads(resp.read())


def _safe_read(exc) -> str:
    try:
        return exc.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return ""


def _redact(text: str) -> str:
    """Strip any credential material before logging an error body."""
    for marker in ("X-Amz-Security-Token=", "X-Amz-Credential=", "X-Amz-Signature="):
        text = re.sub(re.escape(marker) + r"[^&\s'\"]+", marker + "<REDACTED>", text)
    return text


class BedrockClient:
    """Provider-agnostic wrapper exposing explain_risk()/generate_fix()."""

    def __init__(
        self,
        client=None,
        sleeper=time.sleep,
        provider: str = None,
        http_post=None,
        token_generator=None,
    ):
        self._provider = provider or PROVIDER
        self._sleep = sleeper
        self._http_post = http_post or _http_post_json
        self._token_generator = token_generator or generate_bedrock_bearer_token
        if self._provider == "anthropic":
            self._client = (
                client if client is not None else boto3.client("bedrock-runtime")
            )
        else:
            self._client = client  # unused for openai_compat (kept for test injection)

    # ── public surface ──────────────────────────────────────────────────────
    def explain_risk(self, prompt: str) -> str:
        if self._provider == "openai_compat":
            return self._openai_chat(OPENAI_EXPLAIN_MODEL, prompt, OPENAI_EXPLAIN_MAX_TOKENS)
        return self.invoke_model(EXPLAIN_MODEL, prompt, EXPLAIN_MAX_TOKENS)

    def generate_fix(self, prompt: str) -> str:
        if self._provider == "openai_compat":
            return self._openai_chat(OPENAI_FIX_MODEL, prompt, OPENAI_FIX_MAX_TOKENS)
        return self.invoke_model(FIX_MODEL, prompt, FIX_MAX_TOKENS)

    # ── anthropic (boto3 invoke_model, Anthropic Messages API) ───────────────
    def invoke_model(self, model_id: str, prompt: str, max_tokens: int) -> str:
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
                return self._extract_anthropic_text(payload)
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                if code in _THROTTLE_CODES and attempt < MAX_RETRIES:
                    self._sleep(2 ** attempt)
                    attempt += 1
                    continue
                logger.error(
                    json.dumps({"event": "bedrock_invoke_failed", "error_code": code})
                )
                raise

    # ── openai_compat (gpt-oss via runtime bearer token) ─────────────────────
    def _openai_chat(self, model: str, prompt: str, max_tokens: int) -> str:
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": max_tokens,
        }
        attempt = 0
        while True:
            # fresh short-lived token per attempt — never stored or logged
            token = self._token_generator(region=BEDROCK_REGION)
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            try:
                resp = self._http_post(
                    f"{OPENAI_ENDPOINT}/chat/completions", headers, body
                )
                return self._extract_openai_text(resp)
            except urllib.error.HTTPError as exc:
                if exc.code in (429, 500, 503) and attempt < MAX_RETRIES:
                    self._sleep(2 ** attempt)
                    attempt += 1
                    continue
                logger.error(
                    json.dumps(
                        {
                            "event": "openai_compat_failed",
                            "status": exc.code,
                            "detail": _redact(_safe_read(exc))[:500],
                        }
                    )
                )
                raise

    @staticmethod
    def _extract_anthropic_text(payload: dict) -> str:
        for block in payload.get("content", []):
            if block.get("type") == "text":
                return block.get("text", "").strip()
        return ""

    @staticmethod
    def _extract_openai_text(payload: dict) -> str:
        choices = payload.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        # gpt-oss reasoning models put the answer in `content`; fall back to reasoning
        return (message.get("content") or message.get("reasoning") or "").strip()
