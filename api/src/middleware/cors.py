"""CORS headers + JSON response builder for the API handler.

DynamoDB returns numbers as Decimal — `make_response` walks the payload and
coerces them to int/float so `json.dumps` never raises on a scan/finding record.
"""
import json
import os
from decimal import Decimal

# The CloudFront domain is the only allowed origin in staging/prod; "*" in dev
# so the local Vite dev server (http://localhost:5173) can call the API.
# CORS_ORIGIN is injected by CDK from the CloudFront URL (Phase 8) or left "*".
CORS_ORIGIN = os.environ.get("CORS_ORIGIN", "*")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": CORS_ORIGIN,
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Content-Type": "application/json",
}


def _jsonable(obj):
    """Recursively coerce DynamoDB Decimals to native numbers for json.dumps."""
    if isinstance(obj, list):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj


def make_response(status: int, body) -> dict:
    return {
        "statusCode": status,
        "headers": CORS_HEADERS,
        "body": json.dumps(_jsonable(body)),
    }


def preflight() -> dict:
    """Response to a CORS preflight OPTIONS request (no auth, no body)."""
    return {"statusCode": 204, "headers": CORS_HEADERS, "body": ""}
