"""
Phase 11 load test — Enterprise Security Guardrail Auditor REST API.

Simulates concurrent clients driving the real scan pipeline end to end:
  1. POST /v1/scans            -> { presigned_url, scan_job_id }
  2. PUT  <presigned_url>      -> upload a (bad) IaC file straight to S3
  3. GET  /v1/scans/{id}       -> poll until COMPLETE / AI_COMPLETE / REPORT_COMPLETE

Every request carries a Cognito ID token (Bearer) — the API Gateway Cognito
authorizer rejects anything else with 401.

USAGE
  pip install locust boto3 requests
  # Provide a token directly (fastest — no boto3 needed):
  export API_URL="https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/"
  export ID_TOKEN="<cognito id token>"
  # ...or let the file mint one from a Cognito user pool:
  export COGNITO_CLIENT_ID="..." COGNITO_USERNAME="..." COGNITO_PASSWORD="..."
  export AWS_REGION="us-east-1"

  locust -f locustfile.py --headless -u 50 -r 10 -t 3m --host "$API_URL"

ACCEPTANCE TARGET (CLAUDE.md Phase 11): 50 concurrent users, 50 scans, all
complete, 0 Lambda errors.

NOTE — account quota caveat: this demo account's Lambda concurrency limit is 10
(reduced unverified-account quota). At -u 50 the pipeline still completes but
serializes behind that limit; for a true 50-in-flight test the account
concurrency quota must first be raised (see CLAUDE.md Phase 11 note).
"""

import os
import time
import uuid

import requests
from locust import HttpUser, between, task

# A minimal intentionally-bad Terraform file — triggers S3-001/002/004.
BAD_TF = """
resource "aws_s3_bucket" "public_demo" {
  bucket = "loadtest-public-bucket-%s"
  acl    = "public-read"
}
""".strip()


def _resolve_id_token() -> str:
    """Use ID_TOKEN if present, else mint one from Cognito USER_PASSWORD_AUTH."""
    token = os.environ.get("ID_TOKEN")
    if token:
        return token

    client_id = os.environ["COGNITO_CLIENT_ID"]
    username = os.environ["COGNITO_USERNAME"]
    password = os.environ["COGNITO_PASSWORD"]
    region = os.environ.get("AWS_REGION", "us-east-1")

    import boto3

    cognito = boto3.client("cognito-idp", region_name=region)
    resp = cognito.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": password},
    )
    return resp["AuthenticationResult"]["IdToken"]


# Resolve once at import — every simulated user shares the same identity.
_ID_TOKEN = _resolve_id_token()


class ScanUser(HttpUser):
    """One simulated client uploading IaC and polling for the result."""

    wait_time = between(1, 3)

    def on_start(self):
        self.client.headers.update({"Authorization": f"Bearer {_ID_TOKEN}"})

    @task
    def upload_and_poll(self):
        # 1. Request a presigned upload URL + a scan_job_id.
        with self.client.post(
            "v1/scans",
            json={"file_name": f"loadtest-{uuid.uuid4().hex[:8]}.tf"},
            name="POST /v1/scans",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"create scan failed: {resp.status_code} {resp.text[:200]}")
                return
            body = resp.json()
            presigned_url = body["presigned_url"]
            scan_job_id = body["scan_job_id"]
            resp.success()

        # 2. PUT the file straight to S3 (not counted against the API host).
        payload = (BAD_TF % uuid.uuid4().hex[:8]).encode()
        put = requests.put(presigned_url, data=payload, timeout=30)
        if put.status_code not in (200, 204):
            return

        # 3. Poll the scan to terminal state (bounded — don't hang a worker).
        deadline = time.time() + 180
        terminal = {"COMPLETE", "AI_COMPLETE", "REPORT_COMPLETE", "FAILED"}
        while time.time() < deadline:
            with self.client.get(
                f"v1/scans/{scan_job_id}",
                name="GET /v1/scans/{id}",
                catch_response=True,
            ) as poll:
                if poll.status_code != 200:
                    poll.failure(f"poll failed: {poll.status_code}")
                    break
                poll.success()
                if poll.json().get("status") in terminal:
                    break
            time.sleep(5)
