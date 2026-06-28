#!/usr/bin/env python3
"""Wake the demo before a client call — re-enable delivery + seed fresh data.

Inverse of demo_sleep.py:
  1. Re-enable the CloudFront distribution (if one is deployed).
  2. Seed pre-canned demo scans so the dashboard opens with content.
  3. Record {state: awake, timestamp} in SSM /guardrail/{env}/demo-state.
  4. Print the live dashboard URL.

CURRENT ACCOUNT REALITY: CloudFront is blocked, so the dashboard is the Lambda
Function URL host (/guardrail/{env}/frontend-url) — always on, $0 idle, nothing
to re-enable. Step 1 is then a no-op and the script just seeds + prints the URL.

Idempotent. Run the night before a demo; allow ~15 min if CloudFront is in use.

Usage:
  AWS_PROFILE=aws-admin python scripts/demo_wake.py --env dev
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

# Reuse the seeder in-process (same interpreter, same ambient creds).
import seed_demo_data

# Windows consoles default to cp1252; force UTF-8 so dashes/symbols don't mojibake.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _get_ssm(ssm, name: str) -> str | None:
    try:
        return ssm.get_parameter(Name=name)["Parameter"]["Value"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "ParameterNotFound":
            return None
        raise


def _put_ssm(ssm, name: str, value: str) -> None:
    ssm.put_parameter(Name=name, Value=value, Type="String", Overwrite=True)


def _enable_cloudfront(region: str, dist_id: str) -> None:
    cf = boto3.client("cloudfront", region_name=region)
    cfg = cf.get_distribution_config(Id=dist_id)
    etag = cfg["ETag"]
    config = cfg["DistributionConfig"]
    if config["Enabled"]:
        print(f"CloudFront {dist_id} already enabled.")
        return
    config["Enabled"] = True
    cf.update_distribution(Id=dist_id, IfMatch=etag, DistributionConfig=config)
    print(f"CloudFront {dist_id} enabling (propagates in ~15 min).")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default=os.environ.get("DEPLOY_ENV", "dev"))
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", "us-east-1"))
    args = parser.parse_args()

    ssm = boto3.client("ssm", region_name=args.region)

    # 1. Re-enable CloudFront if present.
    dist_id = _get_ssm(ssm, f"/guardrail/{args.env}/cloudfront-dist-id")
    if dist_id:
        _enable_cloudfront(args.region, dist_id)
    else:
        print(
            "No CloudFront distribution — dashboard is the always-on Lambda "
            "Function URL host (nothing to re-enable)."
        )

    # 2. Seed demo data (delegates to seed_demo_data.main with our env/region).
    print()
    sys.argv = ["seed_demo_data", "--env", args.env, "--region", args.region]
    rc = seed_demo_data.main()
    if rc != 0:
        print("WARNING: demo data seeding failed.", file=sys.stderr)
        return rc

    # 3. Record awake state.
    _put_ssm(
        ssm,
        f"/guardrail/{args.env}/demo-state",
        json.dumps({"state": "awake", "timestamp": datetime.now(timezone.utc).isoformat()}),
    )

    # 4. Print the dashboard URL (Function URL host, or CloudFront if deployed).
    url = (
        _get_ssm(ssm, f"/guardrail/{args.env}/frontend-url")
        or _get_ssm(ssm, f"/guardrail/{args.env}/cloudfront-url")
        or "(no frontend URL in SSM — deploy the frontend host first)"
    )
    print(f"\nDemo awake. Dashboard: {url}")
    if dist_id:
        print("Allow ~15 min for CloudFront propagation, then verify login.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
