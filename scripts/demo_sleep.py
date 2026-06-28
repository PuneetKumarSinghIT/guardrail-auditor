#!/usr/bin/env python3
"""Put the demo to sleep between client calls — minimise idle cost.

The whole stack is serverless (Lambda + DynamoDB + S3 + EventBridge), so it
ALREADY costs ~$0 when nobody is using it — there are no servers to stop. The
one resource that can incur standing cost while "on" is a CloudFront
distribution, so sleep disables it (does NOT delete it — config is preserved).

CURRENT ACCOUNT REALITY: CloudFront is blocked pending AWS account verification,
so the dashboard is served by a $0-idle Lambda Function URL host. In that case
there is genuinely nothing to disable — this script records the sleep state and
explains that idle cost is already at the floor.

Idempotent. Records {state: sleeping, timestamp} in SSM /guardrail/{env}/demo-state.

Usage:
  AWS_PROFILE=aws-admin python scripts/demo_sleep.py --env dev
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

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


def _disable_cloudfront(region: str, dist_id: str) -> bool:
    cf = boto3.client("cloudfront", region_name=region)
    cfg = cf.get_distribution_config(Id=dist_id)
    etag = cfg["ETag"]
    config = cfg["DistributionConfig"]
    if not config["Enabled"]:
        print(f"CloudFront {dist_id} already disabled.")
        return True
    config["Enabled"] = False
    cf.update_distribution(Id=dist_id, IfMatch=etag, DistributionConfig=config)
    print(f"CloudFront {dist_id} disabling (propagates in ~1 min).")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default=os.environ.get("DEPLOY_ENV", "dev"))
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", "us-east-1"))
    args = parser.parse_args()

    ssm = boto3.client("ssm", region_name=args.region)
    dist_id = _get_ssm(ssm, f"/guardrail/{args.env}/cloudfront-dist-id")

    if dist_id:
        _disable_cloudfront(args.region, dist_id)
    else:
        print(
            "No CloudFront distribution found "
            f"(/guardrail/{args.env}/cloudfront-dist-id is unset).\n"
            "The dashboard is served by the $0-idle Lambda Function URL host — "
            "nothing to disable."
        )

    _put_ssm(
        ssm,
        f"/guardrail/{args.env}/demo-state",
        json.dumps({"state": "sleeping", "timestamp": datetime.now(timezone.utc).isoformat()}),
    )

    print(
        "\nDemo sleeping. Lambda/DynamoDB/S3 cost $0 at idle; total idle ~$4/month "
        "(KMS + log retention).\nRun demo_wake.py before the next client call."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
