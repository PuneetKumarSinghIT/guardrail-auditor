#!/usr/bin/env python3
"""Seed the rules-catalog-{env} DynamoDB table from rules/rules-catalog.json.

The rules engine (scanner/src/handlers/rules_engine.py) loads ENABLED rules from
this table at scan time (`scan` with `enabled = true`). A freshly deployed
environment has an EMPTY rules-catalog table, so this MUST run as part of
environment bootstrap — otherwise the custom-rule scan layer produces nothing
and only the Checkov layer fires. This is the single step that makes a fresh
demo environment actually find the custom S3-/SG-/IAM-/ENC-/LOG- rules.

Idempotent: re-running overwrites each rule by its `rule_id` primary key.

Usage:
  AWS_PROFILE=aws-admin python scripts/seed_rules_catalog.py --env dev
  DEPLOY_ENV=staging python scripts/seed_rules_catalog.py        # env from DEPLOY_ENV
"""
import argparse
import json
import os
import sys

import boto3


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default=os.environ.get("DEPLOY_ENV", "dev"))
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", "us-east-1"))
    parser.add_argument(
        "--catalog",
        default=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "rules", "rules-catalog.json"
        ),
    )
    args = parser.parse_args()

    table_name = f"rules-catalog-{args.env}"
    catalog_path = os.path.abspath(args.catalog)

    with open(catalog_path) as fh:
        rules = json.load(fh)

    if not isinstance(rules, list) or not rules:
        print(f"ERROR: {catalog_path} must be a non-empty JSON list", file=sys.stderr)
        return 1

    table = boto3.resource("dynamodb", region_name=args.region).Table(table_name)
    with table.batch_writer() as batch:
        for rule in rules:
            if "rule_id" not in rule:
                print(f"ERROR: rule missing 'rule_id': {rule}", file=sys.stderr)
                return 1
            batch.put_item(Item=rule)

    print(f"Seeded {len(rules)} rules into {table_name} ({args.region})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
