"""Static SPA host — serves the React dashboard bundle from the S3 dashboard
bucket behind a public Lambda Function URL (HTTPS, $0 idle).

This is the stopgap delivery path while CloudFront is blocked by AWS account
verification. The CloudFront stack (frontend-stack.ts) stays the durable target;
this Lambda serves the SAME bundle (the 04-deploy-frontend.yml workflow syncs
dist/ to the dashboard bucket either way), so no rebuild is needed when CloudFront
is unblocked.

Lambda Function URL payload format 2.0 → event["rawPath"] carries the request path.
SPA routing: a path with no file extension (a client-side route like /scans/123)
falls back to index.html; a missing asset WITH an extension returns 404.
"""
import base64
import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DASHBOARD_BUCKET = os.environ["DASHBOARD_BUCKET"]

s3_client = boto3.client("s3")

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".map": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
    ".webp": "image/webp",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".txt": "text/plain; charset=utf-8",
}

INDEX_KEY = "index.html"


def _content_type(key: str) -> str:
    _, ext = os.path.splitext(key)
    return CONTENT_TYPES.get(ext.lower(), "application/octet-stream")


def _response(status: int, body: bytes, content_type: str, cache: str) -> dict:
    return {
        "statusCode": status,
        "headers": {"content-type": content_type, "cache-control": cache},
        "body": base64.b64encode(body).decode("ascii"),
        "isBase64Encoded": True,
    }


def _serve(key: str) -> dict:
    obj = s3_client.get_object(Bucket=DASHBOARD_BUCKET, Key=key)
    data = obj["Body"].read()
    cache = (
        "no-cache, must-revalidate"
        if key == INDEX_KEY
        else "public, max-age=31536000, immutable"
    )
    return _response(200, data, _content_type(key), cache)


def handler(event: dict, context) -> dict:
    raw_path = (event.get("rawPath") or "/").lstrip("/")
    key = raw_path if raw_path else INDEX_KEY

    try:
        return _serve(key)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code not in ("NoSuchKey", "404", "AccessDenied"):
            logger.error(json.dumps({"event": "s3_error", "key": key, "code": code}))
            raise
        # Asset miss: a path with an extension is a real 404; an extension-less
        # path is a client-side route → serve the SPA shell.
        if "." in os.path.basename(key):
            logger.info(json.dumps({"event": "asset_404", "key": key}))
            return _response(404, b"Not Found", "text/plain; charset=utf-8", "no-cache")
        logger.info(json.dumps({"event": "spa_fallback", "key": key}))
        return _serve(INDEX_KEY)
