"""API handler — one Lambda behind API Gateway REST (Cognito authorizer).

Routes (all require a valid Cognito JWT):
  POST /v1/scans                      -> presigned upload URL + scan_job_id
  GET  /v1/scans                      -> list scans (max 50, newest first)
  GET  /v1/scans/{scan_job_id}        -> scan detail + findings
  GET  /v1/scans/{scan_job_id}/report -> presigned PDF URL (15 min)

Named app.py (not main.py) on purpose: scanner already owns the `src.main`
module, and all three services share one `src` namespace in the pytest session.
"""
import json
import logging

from src.middleware.auth import Unauthorized, get_claims
from src.middleware.cors import make_response, preflight
from src.routes import reports, scans

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _path_param(event: dict, name: str) -> str | None:
    return (event.get("pathParameters") or {}).get(name)


def handler(event: dict, context) -> dict:
    method = (event.get("httpMethod") or "").upper()
    resource = event.get("resource") or event.get("path") or ""

    if method == "OPTIONS":
        return preflight()

    # ── Auth: every route requires a valid Cognito JWT ───────────────────────
    try:
        claims = get_claims(event)
    except Unauthorized as exc:
        logger.warning(json.dumps({"event": "unauthorized", "reason": str(exc)}))
        return make_response(401, {"error": "Unauthorized"})

    try:
        body = json.loads(event["body"]) if event.get("body") else {}
    except (ValueError, TypeError):
        return make_response(400, {"error": "Invalid JSON body"})

    scan_job_id = _path_param(event, "scan_job_id")
    is_scans_root = resource.rstrip("/").endswith("/v1/scans") or resource in (
        "/v1/scans",
        "v1/scans",
    )

    try:
        if is_scans_root and method == "POST":
            status, payload = scans.create_scan(claims, body)
        elif is_scans_root and method == "GET":
            status, payload = scans.list_scans(claims, event.get("queryStringParameters") or {})
        elif resource.endswith("/report") and method == "GET":
            status, payload = reports.get_report_url(claims, scan_job_id)
        elif scan_job_id and method == "GET":
            status, payload = scans.get_scan(claims, scan_job_id)
        else:
            status, payload = 404, {"error": f"No route for {method} {resource}"}
    except Exception:  # noqa: BLE001 — last-resort guard, never leak a stack trace
        logger.exception("route_error")
        return make_response(500, {"error": "Internal server error"})

    return make_response(status, payload)
