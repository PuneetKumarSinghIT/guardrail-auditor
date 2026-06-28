# Enterprise Security Guardrail Auditor

[![AWS CDK](https://img.shields.io/badge/IaC-AWS_CDK_v2-FF9900?logo=amazonaws&logoColor=white)](https://aws.amazon.com/cdk/)
[![Python](https://img.shields.io/badge/Backend-Python_3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/Frontend-React_18_+_TypeScript-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Amazon Bedrock](https://img.shields.io/badge/AI-Amazon_Bedrock_(Claude)-232F3E?logo=amazonaws&logoColor=white)](https://aws.amazon.com/bedrock/)
[![Serverless](https://img.shields.io/badge/Architecture-Serverless_($0_idle)-6f42c1)](#cost)

> Upload an Infrastructure-as-Code file. Get back a prioritised risk report —
> in plain English, with the exact fix, and a PDF in your inbox — in about a
> minute. Entirely serverless, so it costs roughly nothing when idle.

---

## What it does

The Guardrail Auditor scans **Terraform** and **CloudFormation** files for
security misconfigurations before they ever reach AWS. It runs two scan layers
(a custom 20-rule engine *and* the open-source Checkov scanner), then asks
**Amazon Bedrock (Claude)** to explain each finding in plain English and to
generate the corrected IaC. You get a visual Risk Score dashboard, an emailed
PDF report, and a one-click fix for every critical issue.

It is built as a portfolio demonstration of an enterprise-grade, AI-powered,
event-driven serverless system on AWS.

---

## Key capabilities

- **20+ built-in security rules** across S3, IAM, networking, encryption, and logging — plus the full Checkov ruleset (1,000+ checks) running in Fargate.
- **AI risk explanations** — every finding gets a 2–3 sentence plain-English explanation from Claude. No security jargon required to act on it.
- **AI auto-remediation** — every CRITICAL/HIGH finding ships with a generated, corrected IaC block you can paste straight back into your code.
- **Risk Score dashboard** — a single 0–100 score with colour-coded severity (green → amber → red → dark red), a sortable findings table, and a slide-in AI drawer.
- **Emailed PDF report** — a full report (all severities + compliant resources) lands in your inbox on completion, with a CRITICAL/HIGH summary in the body.
- **Serverless & event-driven** — no servers, no NAT gateway, no database to manage. ~$0 at idle.

---

## Architecture

```
                      ┌─────────────┐
   Upload IaC ───────▶│  S3 uploads │──ObjectCreated──▶ EventBridge
   (dashboard /       └─────────────┘                       │
    presigned PUT)                                          ▼
                                                   ┌──────────────────┐
                                                   │  ingest (Lambda) │  create job (DynamoDB)
                                                   └────────┬─────────┘
                                                ScanRequested│
                                   ┌─────────────────────────┴───────────────┐
                                   ▼                                          ▼
                       ┌────────────────────┐                    ┌────────────────────┐
                       │ rules-engine (ECS) │                    │   checkov (ECS)    │
                       │  20 custom rules   │                    │  OSS scanner       │
                       └─────────┬──────────┘                    └─────────┬──────────┘
                                 │ findings                      SQS results│
                                 ▼                                          ▼
                           DynamoDB findings ◀────────────────  aggregator (Lambda) dedup
                                 │ ScanComplete
                                 ▼
                       ┌────────────────────┐   AIAnalysisComplete   ┌────────────────────┐
                       │ ai-analyzer Lambda │ ─────────────────────▶ │ report (Lambda)    │
                       │  Bedrock (Claude)  │                        │  PDF → S3          │
                       │ explain + fix +    │                        └─────────┬──────────┘
                       │ risk score         │              ReportGenerated      │
                       └────────────────────┘                                  ▼
                                                                    ┌────────────────────┐
   React dashboard ◀── API Gateway ── api Lambda ── DynamoDB        │ email (Lambda) SES │
   (S3 + CloudFront /   (Cognito JWT)                               │  PDF + summary     │
    Lambda Function URL)                                            └────────────────────┘

   Cross-cutting: CloudWatch dashboard + alarms, X-Ray tracing on every Lambda,
                  failure-handler (Lambda) on any ECS exit≠0 / DLQ → failure email.
```

**Flow:** upload → ingest → two-layer scan → aggregate → AI analysis → PDF report → email.
Every hop is an EventBridge event; every compute unit is a container image from ECR.

---

## Tech stack

| Layer | Technology |
|---|---|
| Infrastructure | AWS CDK v2 (TypeScript) → CloudFormation |
| Compute | Lambda (container images) + ECS Fargate |
| Data | DynamoDB (pay-per-request), S3, Secrets Manager |
| Eventing | EventBridge, SQS |
| AI | Amazon Bedrock — Claude (Haiku explain / Sonnet fix) |
| Scanners | Custom Python rules engine + Checkov (OSS) |
| API | API Gateway REST + Cognito (JWT auth) |
| Frontend | React 18 + TypeScript + Vite + Tailwind, React Query, Amplify |
| Notifications | Amazon SES (PDF report email) |
| Observability | CloudWatch dashboard + alarms, AWS X-Ray |
| CI/CD | GitHub Actions (OIDC — no stored AWS keys) |

---

## Deploy it yourself

Prerequisites: an AWS account (CDK-bootstrapped), Docker, Node 20+, Python 3.12,
and Bedrock model access enabled in `us-east-1`.

```bash
# 1. Clone
git clone https://github.com/PuneetKumarSinghIT/guardrail-auditor.git
cd guardrail-auditor

# 2. Bootstrap CDK (once per account/region)
npx cdk bootstrap aws://<ACCOUNT_ID>/us-east-1

# 3. Bring up an entire environment (infra → images → Lambdas → seed rules)
AWS_PROFILE=<your-profile> scripts/deploy_env.sh dev
```

`deploy_env.sh` handles the ECR bootstrap ordering for you. Tear the whole thing
back down to a $0, empty account with one command:

```bash
AWS_PROFILE=<your-profile> npx cdk destroy --all --context env=dev --force
```

---

## Demo lifecycle

The demo can sleep between client calls and wake the night before:

```bash
python scripts/demo_wake.py   --env dev   # re-enable delivery + seed sample scans
python scripts/demo_sleep.py  --env dev   # minimise idle cost between calls
python scripts/billing_check.py           # current month spend, grouped by service
```

---

## Cost

Built serverless-first specifically so it costs almost nothing when nobody is
using it — there is no NAT gateway, no RDS, no EC2, no idle cluster.

| State | Approx. monthly cost |
|---|---|
| Idle (sleep mode) | < $5 (KMS key + log retention) |
| Development month | < $15 |
| Active demo month | < $20 (~650 demo sessions) |
| Per client demo session | ~$0.03 |

---

## Screenshots

_Add dashboard, Scan Detail, and AI-fix screenshots here after a live demo run._

- `docs/screenshots/scan-list.png` — Scan List with risk scores and status
- `docs/screenshots/scan-detail.png` — Risk meter + findings table
- `docs/screenshots/ai-drawer.png` — AI explanation + generated fix

---

_Built by Puneet Kumar Singh as an enterprise AWS portfolio project._
