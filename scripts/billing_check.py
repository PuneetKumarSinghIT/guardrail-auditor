#!/usr/bin/env python3
"""Print the current month's AWS spend, grouped by service.

Uses the Cost Explorer API (get_cost_and_usage) for the current calendar month
to date, groups by SERVICE, prints a table sorted by cost descending, and warns
if the total exceeds the dev budget guardrail ($15/month from CLAUDE.md).

NOTES:
  - Cost Explorer is only available in us-east-1 regardless of where resources
    live — the client is pinned there.
  - Cost Explorer charges $0.01 per paginated request. This makes one request.
  - Cost data lags ~24h, so "today" may read low. That's expected.

Usage:
  AWS_PROFILE=aws-admin python scripts/billing_check.py
  AWS_PROFILE=aws-admin python scripts/billing_check.py --warn-at 20
"""
import argparse
import sys
from datetime import date

import boto3

# Windows consoles default to cp1252, which can't encode box-drawing/arrows.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DEFAULT_WARN_AT = 15.0  # CLAUDE.md development-phase budget target


def _month_to_date() -> tuple[str, str]:
    today = date.today()
    start = today.replace(day=1)
    # Cost Explorer 'End' is exclusive; use tomorrow so today is included.
    end = today.fromordinal(today.toordinal() + 1)
    return start.isoformat(), end.isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warn-at", type=float, default=DEFAULT_WARN_AT)
    args = parser.parse_args()

    start, end = _month_to_date()
    ce = boto3.client("ce", region_name="us-east-1")
    resp = ce.get_cost_and_usage(
        TimePeriod={"Start": start, "End": end},
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )

    rows = []
    unit = "USD"
    for group in resp.get("ResultsByTime", []):
        for g in group.get("Groups", []):
            amount = float(g["Metrics"]["UnblendedCost"]["Amount"])
            unit = g["Metrics"]["UnblendedCost"].get("Unit", unit)
            if amount > 0:
                rows.append((g["Keys"][0], amount))

    rows.sort(key=lambda r: r[1], reverse=True)
    total = sum(a for _, a in rows)

    print(f"AWS cost {start} -> {end} (month to date), {unit}")
    print("-" * 52)
    if not rows:
        print("  (no billable usage yet this month)")
    for service, amount in rows:
        print(f"  {service:<40s} {amount:>9.2f}")
    print("-" * 52)
    print(f"  {'TOTAL':<40s} {total:>9.2f}")

    if total > args.warn_at:
        print(f"\n[WARN] Total ${total:.2f} exceeds the ${args.warn_at:.2f} budget guardrail.")
        return 1
    print(f"\n[OK] Within the ${args.warn_at:.2f} budget guardrail.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
