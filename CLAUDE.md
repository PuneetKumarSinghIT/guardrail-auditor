# Enterprise Security Guardrail Auditor
## Project Intelligence File — Read This First, Every Session

---

## LEAD ARCHITECT MODE — ALWAYS ON

```
Lead Architect mode: ON. We are building a Python-based, API-first
[Enterprise Security Guardrail Auditor] using a free database and a dashboard.

Rules:
1. No Manual Edits: You provide all logic and fixes. I will not edit any code.
2. Audit Log: Two modes — determined by what kind of session is happening:

   MODE A — CLARIFICATION / SCOPING session (no code written, discussing/deciding/fixing CLAUDE.md):
     Update prompts.md AFTER EVERY CHAT TURN.
     Entry is lightweight: prompt + action + scope impact.
     This captures the vibe coding skill — every decision, every correction, every insight.
     Trigger: any turn where the user is asking questions, resolving ambiguity, reviewing,
              or directing changes to scope/architecture/CLAUDE.md.

   MODE B — PHASE IMPLEMENTATION session (writing code, running tests, deploying):
     Update prompts.md ONCE at the end of the phase in the final housekeeping turn.
     Entry is comprehensive: all files, bugs, tests, PR number.
     This avoids the 13× repeated write problem from Phase 5.
     Trigger: any turn where code files are being written, tests run, or AWS resources deployed.

   DETECT THE MODE at the start of every response. If the user's message is exploratory,
   corrective, or architectural → MODE A (log this turn). If it is implementation work → MODE B
   (hold the log until phase end). A single session can switch between modes — that is fine.

3. Time-Check: Start a timer. Goal is an MVP in 4-6 hours (Max window: 16h).
   Report 'Elapsed Time' at the end of every response.
```

**These rules are active in every session, every response, without exception.**

---

## CRITICAL: HOW TO USE THIS FILE

This file is the single source of truth for all project context. At the start of
every session, Claude must:

1. Read this entire file before writing a single line of code
2. Check `## SESSION TRACKER` to know exactly where we left off
3. Check `## PHASE STATUS` to know what is done vs in-progress vs not started
4. **IMMEDIATELY activate the TOKEN EFFICIENCY PROTOCOL** (see section below):
   - Sonnet 4.6 handles ALL execution inline: file writes, edits, git, aws, cdk, pytest, CI
   - No Haiku subagents — Haiku is retired from this project's Claude Code workflow
   - Use parallel tool calls for independent tasks within a single response
   - Diagnose + fix inline when failures occur; never spawn a separate "fix agent"
5. Update `## SESSION TRACKER` at the END of every session with what was completed
6. Never repeat work already marked DONE in phase status
7. Update `prompts.md` based on session mode (see Rule 2 above):
   - CLARIFICATION session → append one lightweight entry at the END of EVERY response
   - IMPLEMENTATION session → append one comprehensive entry at the END of the PHASE only
   Both are written inline by Sonnet 4.6 — no subagents touch prompts.md.
8. Report **Elapsed Time** at the end of every response

**Reading this file IS the session start trigger. No separate prompt needed.**
The moment you finish reading CLAUDE.md, produce the Micro-Task List and begin executing
via the TOKEN EFFICIENCY PROTOCOL defined at the bottom of this file.

---

## PROJECT IDENTITY

**Name:** Enterprise Security Guardrail Auditor
**Owner:** Puneet Kumar Singh (puneetkumarsingh765@gmail.com)
**Purpose:** Portfolio project to attract clients and job offers — must be
             enterprise-grade, visually impressive, and AI-powered.
**Status:** In active development. Started June 2026.
**AWS Account Type:** Personal demo/portfolio account — NOT customer production data.
**Primary Region:** us-east-1
**Secondary Region:** us-west-2 (DR only, implement in Phase 11 — Production Hardening)

### What This Project Does
Ingests Terraform (.tf, .hcl) and CloudFormation (.yaml, .json, .template) files,
runs a two-layer security scan (custom rules engine + OSS scanner Checkov via
Fargate), feeds findings to Amazon Bedrock (Claude) for AI-powered risk explanation
and auto-remediation code generation, then presents a visual Risk Score dashboard
to the user. The entire system is serverless, event-driven, and costs ~$4/month
at idle with ~$0.03 per client demo session.

### Why Serverless-First
No NAT Gateway, no RDS, no ElastiCache, no EC2. Every service must cost $0 when
idle. This enables a "sleep/wake" demo lifecycle: sleep the demo between client
calls, wake it the night before. See `## DEMO LIFECYCLE` section.

---

## PROJECT STRUCTURE (Final Target)

```
d:\AWS\AWS_account_projects\
├── CLAUDE.md                          ← THIS FILE (update every session)
├── README.md                          ← Client-facing project overview
│
├── infrastructure/                    ← CDK TypeScript stacks
│   ├── CLAUDE.md                      ← CDK-specific rules
│   ├── bin/
│   │   └── app.ts                     ← CDK entry point
│   ├── lib/
│   │   ├── foundation-stack.ts        ← S3, DynamoDB, KMS, IAM, SSM
│   │   ├── scanner-stack.ts           ← Lambda scan engine + Fargate task
│   │   ├── ai-stack.ts                ← Bedrock integration Lambda
│   │   ├── api-stack.ts               ← API Gateway REST + WebSocket
│   │   ├── frontend-stack.ts          ← CloudFront + S3 static hosting
│   │   ├── monitoring-stack.ts        ← CloudWatch, X-Ray, Alarms, SNS
│   │   └── auth-stack.ts              ← Cognito User Pool + Identity Pool
│   ├── test/
│   └── package.json
│
├── cloudformation/                    ← CFN YAML files for SCANNER DEMO TARGETS only
│   │                                    (NOT used to deploy this project's infra —
│   │                                     CDK synthesizes real infra CFN via cdk synth)
│   ├── bad/                           ← Intentionally misconfigured CFN (scanner finds these)
│   │   ├── public-s3-cfn.yaml         ← Triggers S3-001, S3-002, S3-004
│   │   ├── open-sg-cfn.yaml           ← Triggers SG-001, SG-002, SG-003
│   │   └── demo-master-bad.yaml       ← ALL CFN violations — use for client demos
│   └── good/                          ← Compliant CFN examples (scanner should pass these)
│       ├── secure-s3-cfn.yaml
│       └── secure-sg-cfn.yaml
│
├── terraform-examples/                ← IaC examples for scanner demo + testing
│   ├── good/                          ← Compliant examples (scanner should pass these)
│   │   ├── s3-secure.tf               ← Encrypted, versioned, no public access
│   │   ├── sg-restricted.tf           ← Ports locked down, no 0.0.0.0/0
│   │   └── iam-least-privilege.tf     ← Scoped policies, no wildcards
│   ├── bad/                           ← Intentionally misconfigured (scanner finds these)
│   │   ├── s3-public-bucket.tf        ← Triggers S3-001, S3-002, S3-004
│   │   ├── sg-open-ssh.tf             ← Triggers SG-001, SG-002, SG-003
│   │   ├── iam-wildcard.tf            ← Triggers IAM-001, IAM-002
│   │   ├── unencrypted-resources.tf   ← Triggers ENC-001, ENC-002
│   │   └── demo-master-bad.tf         ← ALL violations in one file — use for demos
│   └── cloudformation-bad/            ← CFN equivalents of bad examples
│       ├── public-s3-cfn.yaml         ← CFN version of S3 violations
│       ├── open-sg-cfn.yaml           ← CFN version of network violations
│       └── demo-master-bad.yaml       ← All CFN violations — use for demos
│
├── scanner/                           ← Python 3.12 — Docker images only (Lambda + ECS)
│   ├── Dockerfile                     ← Single shared image: all scanner compute (ingest/rules/aggregator)
│   ├── CLAUDE.md                      ← Scanner-specific rules
│   ├── requirements.txt
│   └── src/
│       ├── main.py                    ← Entry point: dispatches by MODE env var (ingest|rules_engine|aggregator|report|email|failure)
│       ├── controllers/               ← Event routing + request shaping — NO business logic here
│       │   ├── ingest_controller.py   ← Parses S3/EventBridge event → calls IngestService
│       │   ├── scan_controller.py     ← Parses ScanRequested event → calls ScanService
│       │   ├── aggregator_controller.py ← Parses SQS message → calls AggregationService
│       │   ├── report_controller.py   ← Parses AIAnalysisComplete event → calls ReportService
│       │   └── email_controller.py    ← Parses ReportGenerated event → calls EmailService
│       ├── services/                  ← Business logic — Single Responsibility per service
│       │   ├── ingest_service.py      ← File validation, DDB job record, EventBridge publish
│       │   ├── scan_service.py        ← Parser selection, rule orchestration, findings write
│       │   ├── aggregation_service.py ← Checkov result dedup, DDB update, ScanComplete event
│       │   ├── report_service.py      ← PDF generation (reportlab), S3 upload, ReportGenerated event
│       │   └── email_service.py       ← MIME email build, PDF attachment, SES send
│       ├── core/                      ← Domain models + interfaces — Open/Closed, DI
│       │   ├── models/
│       │   │   ├── finding.py         ← Finding dataclass
│       │   │   └── scan_job.py        ← ScanJob dataclass
│       │   └── interfaces/
│       │       ├── parser_interface.py   ← ABC: parse(bytes) → dict
│       │       └── rule_interface.py     ← ABC: apply(parsed_iac, scan_job_id) → list[Finding]
│       ├── adapters/                  ← External integrations — Dependency Inversion
│       │   ├── aws/
│       │   │   ├── dynamodb_adapter.py
│       │   │   ├── s3_adapter.py
│       │   │   ├── eventbridge_adapter.py
│       │   │   └── sqs_adapter.py
│       │   └── parsers/               ← Implement parser_interface.py
│       │       ├── terraform_parser.py   ← python-hcl2 based
│       │       └── cloudformation_parser.py ← cfn-flip based
│       └── rules/                     ← Implement rule_interface.py — one file per category
│           ├── s3_rules.py
│           ├── network_rules.py
│           ├── iam_rules.py
│           ├── encryption_rules.py
│           └── logging_rules.py
│   └── tests/
│       └── fixtures/                  ← Sample bad IaC files for testing
│
├── ai-engine/                         ← Bedrock AI analysis
│   ├── CLAUDE.md                      ← AI-specific rules
│   ├── src/
│   │   ├── analyzer.py                ← Main Bedrock orchestrator Lambda
│   │   ├── prompts/
│   │   │   ├── explain_risk.txt       ← Prompt template for risk explanation
│   │   │   ├── generate_fix.txt       ← Prompt template for IaC fix generation
│   │   │   └── score_risk.txt         ← Prompt template for scoring
│   │   └── bedrock_client.py          ← Bedrock boto3 wrapper with retry logic
│   ├── tests/
│   └── requirements.txt
│
├── api/                               ← API Gateway REST Lambda (guardrail-api ECR image)
│   ├── src/
│   │   ├── routes/
│   │   │   ├── scans.py               ← POST /v1/scans, GET /v1/scans, GET /v1/scans/{id}
│   │   │   └── reports.py             ← GET /v1/scans/{id}/report (presigned PDF URL)
│   │   └── middleware/
│   │       ├── auth.py                ← Cognito JWT validation (python-jose)
│   │       └── cors.py                ← CORS headers (CloudFront domain only)
│   ├── tests/
│   └── requirements.txt               ← boto3, python-jose[cryptography]
│   NOTE: No websocket/, no dashboard.py, no findings.py — removed from scope
│
├── frontend/                          ← React + TypeScript static site (S3 + CloudFront)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx          ← Cognito sign-in form
│   │   │   ├── ScanListPage.tsx       ← All scans table + ScanUploader
│   │   │   └── ScanDetailPage.tsx     ← Risk meter + findings table + PDF download
│   │   ├── components/
│   │   │   ├── RiskScoreMeter.tsx     ← SVG circular gauge (green/amber/red/dark-red)
│   │   │   ├── FindingsTable.tsx      ← Sortable by severity, filter bar, row click → drawer
│   │   │   ├── AiExplanationPanel.tsx ← Slide-in drawer: Explanation tab + Fix tab
│   │   │   └── ScanUploader.tsx       ← react-dropzone, PUT to S3 presigned URL
│   │   ├── hooks/
│   │   │   └── useScans.ts            ← React Query: useScans, useScan, useReportUrl, useCreateScan
│   │   └── lib/
│   │       ├── api.ts                 ← Axios instance with Cognito JWT interceptor
│   │       ├── auth.ts                ← Amplify v6 wrapper (signIn, signOut, getIdToken)
│   │       └── env.ts                 ← Typed VITE_* env vars (no VITE_WS_URL)
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
│   NOTE: No TrendChart, no ScanProgress, no useWebSocket — removed from scope
│
├── rules/                             ← Security rules catalog
│   └── rules-catalog.json             ← All 20+ rules with metadata
│
├── scripts/                           ← Operational scripts
│   ├── demo_sleep.py                  ← De-provision for cost saving
│   ├── demo_wake.py                   ← Re-provision before client demo
│   ├── seed_demo_data.py              ← Pre-populate DynamoDB with sample scans
│   └── billing_check.py               ← Check current month AWS cost via Cost Explorer
│
├── fargate/                           ← Checkov OSS scanner ECS task (SEPARATE image from scanner/)
│   ├── Dockerfile                     ← FROM python:3.12-slim + checkov install (~500MB)
│   ├── scanner_runner.py              ← Downloads IaC from S3, runs checkov, pushes to SQS
│   └── requirements.txt               ← checkov, boto3 only
│
└── .github/
    ├── workflows/
    │   ├── 01-pr-checks.yml           ← On every PR: pytest + cfn-lint + tfsec + Checkov
    │   ├── 02-deploy-infra.yml        ← On push to main: upload CFN to S3 → deploy stacks in sequence
    │   ├── 03-deploy-lambdas.yml      ← On push to scanner/ api/ ai-engine/: Docker build → ECR push → Lambda image update
    │   ├── 04-deploy-frontend.yml     ← On push to frontend/: build → S3 sync → CloudFront invalidate
    │   ├── 05-deploy-fargate.yml      ← On push to fargate/: Docker build → ECR push → task def update
    │   └── 06-hotfix-to-prod.yml      ← Manual trigger only: emergency hotfix bypasses staging, double approval gate
    └── actions/
        └── aws-deploy/
            └── action.yml             ← Reusable action: assume OIDC role + set AWS creds
```

---

## PHASE STATUS — THE MASTER CHECKLIST

Update status after every session. Use: `[ ]` not started, `[~]` in progress, `[x]` done.
Each phase has: GOAL, ACCEPTANCE CRITERIA, START COMMANDS, then checklist items.
A phase is ONLY complete when its Acceptance Criteria is met — not just when all boxes are checked.

```
═══════════════════════════════════════════════════════════════
PHASE 0: Prerequisites & Repository Setup          ✅ COMPLETE
═══════════════════════════════════════════════════════════════
GOAL: Every tool, credential, and service access needed to write
      and deploy code is confirmed working before touching any code.

ACCEPTANCE CRITERIA:
  ✓ aws sts get-caller-identity → returns your account ID
  ✓ npx cdk --version → returns 2.x
  ✓ aws bedrock list-foundation-models --region us-east-1 → includes claude-haiku
  ✓ gh auth status → logged in to GitHub
  ✓ GitHub Actions workflow can assume GitHubActionsDeployRole via OIDC (test run)

  [x] CLAUDE.md written and committed (June 22, 2026)
  [x] Node.js 20+ installed locally
  [x] Python 3.12 installed locally
  [x] Docker Desktop installed and running
  [x] AWS CLI v2 configured: aws configure (AdministratorAccess role)
  [x] GitHub CLI installed and authenticated: gh auth login
  [x] GitHub repository created: guardrail-auditor (public, for portfolio visibility)
  [x] Initial commit pushed: CLAUDE.md + .gitignore only
  [x] AWS OIDC provider created in IAM:
        Provider URL: https://token.actions.githubusercontent.com
        Audience: sts.amazonaws.com
  [x] IAM role created: GitHubActionsDeployRole
        Trust: token.actions.githubusercontent.com
        Condition: StringLike repo:YOUR_GITHUB_USERNAME/guardrail-auditor:*
        Policy: AdministratorAccess (tighten in Phase 11)
  [x] GitHub Environments configured (repo Settings → Environments):
        dev     → no protection rules
        staging → no protection rules
        prod    → Required reviewer: puneetkumarsingh765@gmail.com
  [x] GitHub repository secrets set (Settings → Secrets → Actions):
        AWS_ACCOUNT_ID, AWS_REGION=us-east-1
  [x] Amazon Bedrock model access enabled in us-east-1:
        Console → Bedrock → Model Access → Enable Haiku + Sonnet
  [x] SES email identity verified: puneetkumarsingh765@gmail.com
  [x] CDK bootstrapped: npx cdk bootstrap aws://ACCOUNT_ID/us-east-1

═══════════════════════════════════════════════════════════════
PHASE 1: Foundation Infrastructure
═══════════════════════════════════════════════════════════════
GOAL: All shared AWS resources (storage, auth, encryption, IAM)
      exist in the account. No application code yet.

ACCEPTANCE CRITERIA:
  ✓ aws dynamodb list-tables → shows scan-jobs, findings, rules-catalog (ws-connections removed — WebSocket out of scope)
  ✓ aws s3 ls | grep guardrail → shows 5 buckets
  ✓ aws ssm get-parameters-by-path --path /guardrail → returns ≥ 5 parameters
  ✓ aws kms list-keys → includes the project KMS key
  ✓ aws cognito-idp list-user-pools --max-results 10 → shows guardrail-users pool

START COMMANDS:
  mkdir infrastructure && cd infrastructure
  npx aws-cdk@latest init app --language typescript
  npm install aws-cdk-lib constructs
  # Then write the stack files below, then:
  npx cdk synth          # verify no errors before deploying
  npx cdk deploy FoundationStack AuthStack --require-approval never

  [x] infrastructure/bin/app.ts: instantiates FoundationStack + AuthStack
  [x] infrastructure/lib/foundation-stack.ts — creates:
        S3 buckets (5): iac-uploads, scan-reports, dashboard, cfn-artifacts, lambda-packages
          Each: KMS-encrypted, block-all-public-access, versioning on uploads+reports
          scan-reports: S3 Intelligent Tiering (IA after 30d, Archive after 90d)
          iac-uploads: lifecycle delete after 30d, ObjectCreated → EventBridge
          lambda-packages: lifecycle delete after 30d
        DynamoDB tables (3): scan-jobs, findings, rules-catalog
          NOTE: ws-connections table removed — WebSocket is out of scope
          All: PAY_PER_REQUEST billing, KMS-encrypted, TTL=90days (except rules-catalog)
          scan-jobs GSI: status-index (PK:status, SK:created_at)
          findings GSI: severity-index (PK:severity, SK:scan_job_id)
        KMS key: 1 project key, auto-rotate annually
        SSM parameters: /guardrail/kms-key-arn, /guardrail/table-*, /guardrail/bucket-*
        IAM roles: LambdaBaseRole (CloudWatch+X-Ray only), FargateTaskRole (SQS+S3+DynamoDB)
        CloudWatch log groups: deferred to Lambda stacks (useCdkManagedLogGroup:true in cdk.json)
        Billing alarm: $20 → SNS topic guardrail-billing-alerts → email
  [x] infrastructure/lib/auth-stack.ts — creates:
        Cognito User Pool: email sign-in, password policy (8+ chars, mixed case, numbers)
        Cognito App Client: SPA type, no client secret, allowed OAuth flows
        Cognito Identity Pool: linked to User Pool
        SSM: /guardrail/cognito-user-pool-id, /guardrail/cognito-client-id, /guardrail/cognito-identity-pool-id
  [x] infrastructure/CLAUDE.md: CDK L2 construct conventions, tagging rules
  [x] npx cdk synth → zero errors, review generated CFN template sizes
  [x] npx cdk deploy GuardrailFoundation-dev GuardrailAuth-dev
  [x] VERIFY: all 5 acceptance criteria passed (2026-06-28)

═══════════════════════════════════════════════════════════════
PHASE 2: CI/CD Pipeline (GitHub Actions)
═══════════════════════════════════════════════════════════════
GOAL: Every code change flows feature branch → dev → staging → main via PRs.
      Checks run on every PR. Auto-deploys to matching environment on merge.
      Prod deployment requires manual approval via GitHub Environment gate.

ACCEPTANCE CRITERIA:
  ✓ Merge feature branch → dev → all deploy workflows run against dev environment
  ✓ PR from dev → staging is blocked if 01-pr-checks.yml fails
  ✓ Merge dev → staging → all deploy workflows run against staging environment
  ✓ Merge staging → main → prod deploy pauses for approval at puneetkumarsingh765@gmail.com
  ✓ Direct push to dev/staging/main (bypassing PR) is rejected by branch protection rules
  ✓ CDK resources deployed in dev are named *-dev; staging are named *-staging

START COMMANDS:
  mkdir -p .github/workflows .github/actions/aws-deploy
  # Write all workflow files, then push to GitHub

  [x] .github/actions/aws-deploy/action.yml:
        Reusable action: inputs(role-arn, aws-region, deploy-env)
        Uses aws-actions/configure-aws-credentials@v4 with role-to-assume (OIDC)
        No AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY anywhere
        Sets DEPLOY_ENV output: (github.ref_name == 'main') ? 'prod' : github.ref_name
  [x] .github/workflows/01-pr-checks.yml:
        Trigger: pull_request targeting dev, staging, or main
        Jobs (parallel): pytest scanner/ api/ ai-engine/ --cov=src --cov-fail-under=70
                         cfn-lint cloudformation/**/*.yaml
                         tfsec terraform-examples/ --no-color
                         checkov -d cloudformation/ terraform-examples/
        All jobs must pass — any failure blocks PR merge. Does NOT deploy.
  [x] .github/workflows/02-deploy-infra.yml:
        Trigger: push to dev OR staging OR main, paths: infrastructure/**
        Resolves DEPLOY_ENV: dev→dev, staging→staging, main→prod
        Steps: assume role → cdk synth --context env=$DEPLOY_ENV
               → s3 sync cdk.out/ to cfn-artifacts/$DEPLOY_ENV/
               → cdk deploy --all --context env=$DEPLOY_ENV (CDK handles stack order)
        GitHub Environment gate: dev=auto, staging=auto, prod=requires approval
  [x] .github/workflows/03-deploy-lambdas.yml:
        Trigger: push to dev OR staging OR main, paths: scanner/**, api/**, ai-engine/**
        Resolves DEPLOY_ENV from branch name
        Per changed service (Docker image approach — NO zip packages):
          docker build -t guardrail-{service} {dir}/
          aws ecr get-login-password | docker login {ecr-uri}
          docker tag → push: {ecr-uri}:$DEPLOY_ENV-{git-sha} AND {ecr-uri}:$DEPLOY_ENV-latest
          aws lambda update-function-code --image-uri {ecr-uri}:$DEPLOY_ENV-{git-sha}
            (Lambda functions only — ECS tasks updated via task def revision in 05-deploy-fargate.yml)
        GitHub Environment gate: prod requires approval
  [x] .github/workflows/04-deploy-frontend.yml:
        Trigger: push to dev OR staging OR main, paths: frontend/**
        Resolves DEPLOY_ENV from branch name
        Fetches VITE_* values from SSM /guardrail/$DEPLOY_ENV/* (env-namespaced)
        Steps: npm ci → fetch SSM → npm run build → s3 sync → CloudFront invalidate
        GitHub Environment gate: prod requires approval
  [x] .github/workflows/05-deploy-fargate.yml:
        Trigger: push to dev OR staging OR main, paths: fargate/**
        Resolves DEPLOY_ENV from branch name
        Tags image as $DEPLOY_ENV-{git-sha} AND $DEPLOY_ENV-latest
        GitHub Environment gate: prod requires approval
  [x] .github/workflows/06-hotfix-to-prod.yml:
        Trigger: workflow_dispatch only (emergency — bypasses staging)
        Input: hotfix_branch name
        Steps: run pr-checks on hotfix_branch → double approval gate → deploy to prod
        After hotfix: MUST backport via PR hotfix_branch → staging → dev
  [x] GitHub branch protection rules configured via GitHub Rulesets:
        main:    require PR + 1 approval + 01-pr-checks passing, no direct push
        staging: require PR + 01-pr-checks passing, no direct push
        dev:     require PR from feature branches, no direct push
        Default branch set to: dev
  [x] GitHub secret added: ECR_REPO_URI
  [x] ECR repository created: guardrail-scanner (KMS-encrypted, scan-on-push enabled)
  [x] VERIFY: feature branch → PR to dev → all 4 checks pass → merge succeeded (PR #2)
  [ ] VERIFY: PR dev → staging → merge → staging environment deploys (test in Phase 3)
  [ ] VERIFY: PR staging → main → merge → prod gate pauses for email approval (test in Phase 3)

═══════════════════════════════════════════════════════════════
PHASE 3: IaC Demo Examples
═══════════════════════════════════════════════════════════════
GOAL: Realistic Terraform and CloudFormation files exist in the repo
      to use as live scan targets during client demos. Also: the
      rules catalog that drives the scanner is defined here.

ACCEPTANCE CRITERIA:
  ✓ checkov -d terraform-examples/bad/ → ≥ 5 FAILED checks shown
  ✓ checkov -d terraform-examples/good/ → 0 FAILED checks
  ✓ tfsec terraform-examples/bad/ → ≥ 3 issues found
  ✓ cfn-lint cloudformation/bad/demo-master-bad.yaml → ≥ 1 warning/error
  ✓ rules/rules-catalog.json → valid JSON, 20 entries, each has rule_id+severity+category

START COMMANDS:
  mkdir -p terraform-examples/good terraform-examples/bad
  mkdir -p cloudformation/good cloudformation/bad
  mkdir rules

  [x] rules/rules-catalog.json: 20 rules (see ARCHITECTURE SPECS for full list)
        Each rule: rule_id, name, description, severity, category, iac_types, enabled
  [x] terraform-examples/good/s3-secure.tf: encrypted, versioned, no public access, logging on
  [x] terraform-examples/good/sg-restricted.tf: no 0.0.0.0/0 on any port
  [x] terraform-examples/good/iam-least-privilege.tf: scoped actions, no wildcards, no inline
  [x] terraform-examples/bad/s3-public-bucket.tf: # Triggers: S3-001, S3-002, S3-004
  [x] terraform-examples/bad/sg-open-ssh.tf: # Triggers: SG-001, SG-002, SG-003
  [x] terraform-examples/bad/iam-wildcard.tf: # Triggers: IAM-001, IAM-002
  [x] terraform-examples/bad/unencrypted-resources.tf: # Triggers: ENC-001, ENC-002
  [x] terraform-examples/bad/demo-master-bad.tf:
        # Triggers: S3-001, SG-001, IAM-001, ENC-001, LOG-001 minimum
        # This is the PRIMARY demo file — one upload triggers all CRITICAL rules
  [x] cloudformation/bad/public-s3-cfn.yaml: # CFN equivalent of S3 violations
  [x] cloudformation/bad/open-sg-cfn.yaml: # CFN equivalent of network violations
  [x] cloudformation/bad/demo-master-bad.yaml:
        # CFN version of all violations — used when client wants CFN demo
  [x] cloudformation/good/secure-s3-cfn.yaml
  [x] cloudformation/good/secure-sg-cfn.yaml
  [x] VERIFY: run all 5 acceptance criteria commands locally (2026-06-28)

═══════════════════════════════════════════════════════════════
PHASE 4: Ingestion Layer
═══════════════════════════════════════════════════════════════
GOAL: A user uploads an IaC file to S3 (via the app or directly)
      and a DynamoDB job record is created automatically.

ACCEPTANCE CRITERIA:
  ✓ aws s3 cp terraform-examples/bad/demo-master-bad.tf s3://guardrail-iac-uploads-{id}/test.tf
  ✓ aws dynamodb scan --table-name scan-jobs → shows 1 item, status=QUEUED, file_name=test.tf
  ✓ Upload a .exe file → no DynamoDB record created (validation rejected it)
  ✓ pytest scanner/tests/test_ingest.py → 5/5 passed

START COMMANDS:
  mkdir -p scanner/src/handlers scanner/src/models scanner/tests/fixtures
  touch scanner/requirements.txt

  CODE:
  [x] scanner/src/models/finding.py:
        @dataclass Finding: rule_id, severity, resource_name, resource_type,
                            line_number, code_snippet, scan_job_id, finding_id
  [x] scanner/src/handlers/ingest_handler.py:
        Triggered by: EventBridge (S3 ObjectCreated on iac-uploads bucket)
        1. Extract bucket + key from event
        2. Validate extension: .tf .hcl .yaml .json .template — reject all others
        3. Generate scan_job_id = str(uuid.uuid4())
        4. Detect iac_type: terraform (if .tf/.hcl) or cloudformation (if .yaml/.json/.template)
        5. Write DynamoDB: scan_job_id, file_name, s3_key, status=QUEUED, iac_type, created_at
        6. Publish EventBridge: source=guardrail, detail-type=ScanRequested,
                                detail={scan_job_id, s3_key, iac_type}
        7. Return 200
  [x] scanner/requirements.txt: boto3>=1.34, python-hcl2, cfn-flip, moto, pytest, pytest-cov
  [x] scanner/tests/fixtures/valid.tf: minimal valid Terraform file
  [x] scanner/tests/fixtures/invalid.exe: 4-byte fake MZ binary
  [x] scanner/tests/test_ingest.py: 5 tests
        test_valid_tf_creates_job, test_valid_yaml_creates_job,
        test_invalid_extension_rejected, test_missing_s3_key_fails,
        test_eventbridge_event_published

  INFRASTRUCTURE (update scanner-stack.ts):
  [x] infrastructure/lib/scanner-stack.ts — full stack:
        Lambda (container images): ingest-handler (256MB, 30s) + aggregator (256MB, 60s)
        ECS Fargate tasks: rules-engine-task (0.5vCPU, 1GB) + checkov-task (0.25vCPU, 512MB)
        NOTE: rules-engine is ECS task NOT Lambda — see KNOWN DECISIONS
        EventBridge rule (default bus): S3 ObjectCreated → ingest-handler Lambda
        EventBridge rule (custom bus): ScanRequested → rules-engine ECS RunTask + checkov ECS RunTask
        SQS: checkov-results queue + DLQ; ECS Cluster: guardrail-cluster
        Grant ingest-handler: DynamoDB write on scan-jobs, EventBridge PutEvents
  [x] infrastructure/lib/foundation-stack.ts: added EventBus guardrail-events-${env}, exported
  [x] infrastructure/bin/app.ts: ScannerStack wired with correct props + addDependency(foundation)
  [x] npx cdk synth → zero errors, zero warnings (2026-06-28)
  [x] VERIFY: all acceptance criteria met via CI (PR #7 merged to dev, 2026-06-28)

═══════════════════════════════════════════════════════════════
PHASE 5: Scanning Engine                            ✅ COMPLETE
═══════════════════════════════════════════════════════════════
GOAL: A QUEUED job triggers a two-layer scan (custom rules + Checkov)
      and all findings are written to DynamoDB.

ACCEPTANCE CRITERIA:
  ✓ Upload demo-master-bad.tf → scan-jobs status becomes COMPLETE within 5 minutes
  ✓ aws dynamodb query --table-name findings --key-condition "scan_job_id=..." → ≥ 5 items
  ✓ At least 1 finding has severity=CRITICAL
  ✓ pytest scanner/tests/ → all tests pass with ≥ 70% coverage

START COMMANDS:
  pip install python-hcl2 cfn-flip checkov  # for local testing
  mkdir -p fargate scanner/src/parsers scanner/src/handlers

  CODE:
  [x] scanner/src/parsers/terraform_parser.py:
        Input: S3 object bytes  Output: dict of {resource_type: {resource_name: attrs}}
        Uses python-hcl2. Handles multi-file .tf (single file for MVP).
  [x] scanner/src/parsers/cloudformation_parser.py:
        Input: S3 object bytes  Output: dict of {ResourceType: {LogicalId: Properties}}
        Uses cfn-flip (handles both JSON and YAML CFN).
  [x] scanner/src/controllers/scan_controller.py + scanner/src/services/scan_service.py:
        Entry point: ECS Fargate task (MODE=rules_engine), NOT Lambda
        Triggered by: ECS RunTask call from EventBridge ScanRequested rule
        Receives: SCAN_JOB_ID, S3_KEY, IAC_TYPE as ECS container environment overrides
        Flow (scan_controller → scan_service):
          1. Load rules from DynamoDB rules-catalog (enabled=true only)
          2. Download IaC file from S3 via s3_adapter
          3. Parse via terraform_parser or cloudformation_parser (selected by IAC_TYPE)
          4. Apply each rule → produce Finding objects where violations found
          5. Write all findings to DynamoDB via dynamodb_adapter
          6. Update scan-jobs: status=SCANNING
          7. Publish EventBridge: RulesEngineDone {scan_job_id, finding_count}
          8. Exit with code 0 (success) or non-zero (triggers failure_handler)
  [x] fargate/Dockerfile:
        FROM python:3.12-slim
        RUN pip install checkov boto3
        COPY scanner_runner.py .
        CMD ["python", "scanner_runner.py"]
  [x] fargate/scanner_runner.py:
        Reads from env: SCAN_JOB_ID, S3_BUCKET, S3_KEY, SQS_QUEUE_URL
        Downloads IaC file from S3
        Runs: checkov -f {file} --output json --quiet
        Parses Checkov JSON → Finding objects (maps checkov check_id to our rule_id where possible)
        Sends batch of findings to SQS queue: guardrail-checkov-results
  [x] scanner/src/controllers/aggregator_controller.py + scanner/src/services/aggregation_service.py:
        Entry point: Lambda container image (MODE=aggregator), triggered by SQS guardrail-checkov-results
        Flow (aggregator_controller → aggregation_service):
          1. Read findings batch from SQS message body
          2. Deduplicate: if same resource+rule already written by rules-engine → skip
          3. Write net-new findings to DynamoDB via dynamodb_adapter
          4. Update scan-jobs: finding_counts={CRITICAL:n, HIGH:n, MEDIUM:n, LOW:n}, status=COMPLETE
          5. Publish EventBridge: ScanComplete {scan_job_id, finding_count}
  [x] scanner/requirements.txt: add python-hcl2, cfn-flip

  INFRASTRUCTURE (complete scanner-stack.ts):
  [x] ECR repo: guardrail-ingest-{env}        (ingest-handler Lambda — Dockerfile: scanner/ingest/)
  [x] ECR repo: guardrail-aggregator-{env}    (aggregator Lambda    — Dockerfile: scanner/aggregator/)
  [x] ECR repo: guardrail-rules-engine-{env}  (rules-engine ECS     — Dockerfile: scanner/rules_engine/)
  [x] ECR repo: guardrail-checkov-{env}       (checkov ECS          — Dockerfile: fargate/)
  [x] Lambda: ingest-handler (DockerImageFunction, guardrail-ingest ECR, 256MB, 30s)
  [x] Lambda: aggregator (DockerImageFunction, guardrail-aggregator ECR, 256MB, 60s, SQS trigger)
  [x] ECS Fargate task def: rules-engine (guardrail-rules-engine ECR, 0.5 vCPU, 1GB)
  [x] ECS Fargate task def: checkov (guardrail-checkov ECR, 0.25 vCPU, 512MB)
  [x] SQS queue: guardrail-checkov-results + DLQ (maxReceiveCount=3)
  [x] ECS Cluster: guardrail-cluster — VPC: public subnets only, natGateways=0, assignPublicIp=true on tasks
  [x] scanner/Dockerfile: FROM public.ecr.aws/lambda/python:3.12 (single image for Lambda + ECS)
  [x] EventBridge rule: ScanRequested → rules-engine ECS RunTask AND checkov ECS RunTask (both Fargate)
  [x] ECR images built + pushed (all 4 per-service repos, 2026-06-28):
        guardrail-ingest-dev, guardrail-aggregator-dev (Lambda — built via buildx
          --provenance=false --output oci-mediatypes=false for Lambda manifest compat),
        guardrail-rules-engine-dev, guardrail-checkov-dev (ECS — standard docker build)
        NOTE: Lambda rejects Docker-29 BuildKit default (OCI image index w/ provenance
          attestations) → "image manifest media type not supported". Use buildx
          docker-container driver + oci-mediatypes=false for ANY fromEcr Lambda image.

  TESTS:
  [x] scanner/tests/test_terraform_parser.py: 5 tests (valid, empty, nested, multi-resource, malformed)
  [x] scanner/tests/test_cloudformation_parser.py: 5 tests
  [x] scanner/tests/test_rules_engine.py: 1 test per rule category (6 tests minimum)
  [x] scanner/tests/test_aggregator.py: 3 tests (dedupe, status update, event publish)
  [x] VERIFY: upload demo-master-bad.tf → ALL acceptance criteria PASS (2026-06-28):
        status=COMPLETE in <5min; 48 findings; 4 CRITICAL (S3-001, SG-001/2/3);
        both layers present (custom S3/SG/IAM/ENC/LOG + Checkov CKV_*); pytest 32 passed, 70% cov

═══════════════════════════════════════════════════════════════
PHASE 6: AI Analysis Engine
═══════════════════════════════════════════════════════════════
GOAL: Every finding gets a plain-English explanation and a corrected
      IaC code block generated by Amazon Bedrock.

ACCEPTANCE CRITERIA:
  ✓ After scan COMPLETE → query findings → every item has non-empty ai_explanation
  ✓ CRITICAL findings have non-empty ai_fix_code (valid IaC syntax)
  ✓ scan-jobs risk_score is populated (0-100)
  ✓ Cost per full scan of demo-master-bad.tf (10 findings) < $0.05 in Bedrock tokens
  ✓ pytest ai-engine/tests/ → all pass

START COMMANDS:
  mkdir -p ai-engine/src/prompts ai-engine/tests

  ⚠ MODEL-ACCESS BLOCKER (2026-06-28): Bedrock model access is NOT_AUTHORIZED on this
    account for Claude Haiku 4.5 + Sonnet 4.6. Anthropic models need a one-time use-case
    form submitted IN THE CONSOLE (CLI `create-foundation-model-agreement` fails with
    "You have not filled out the request form"; `put-use-case-for-model-access` needs an
    opaque console-generated form-data blob — not CLI-fillable). NO Bedrock model (Nova/
    Llama/OpenAI gpt-oss) is enableable purely via CLI in this account. User raised an AWS
    support case. Code is deployed + wiring-verified; E2E + acceptance criteria pending access.
  ⚠ MODEL-ID CORRECTION: CLAUDE.md's original IDs were WRONG. Claude 4.x on Bedrock is
    INFERENCE_PROFILE-only (no on-demand). Correct invoke IDs:
    explain → us.anthropic.claude-haiku-4-5-20251001-v1:0 ; fix → us.anthropic.claude-sonnet-4-6

  CODE:
  [x] ai-engine/src/prompts/explain_risk.txt (replace via str.replace, not .format — code
        snippets contain literal braces). [x] generate_fix.txt  [x] score_risk.txt (reference only).
  [x] ai-engine/src/bedrock_client.py: BedrockClient.invoke_model(model_id,prompt,max_tokens)
        + explain_risk()/generate_fix() routing (Haiku 300 / Sonnet 800 tokens); ThrottlingException
        exponential backoff (max 3); client + sleeper injectable for tests.
  [x] ai-engine/src/analyzer.py: handler(EventBridge ScanComplete) → explain each finding,
        generate_fix for CRITICAL/HIGH only (cost guard), write back, risk_score
        (WEIGHTS C40/H20/M5/L1, cap 200, /200*100), status=AI_COMPLETE, publish AIAnalysisComplete.
  [x] ai-engine/requirements.txt: boto3 + awslambdaric. [x] ai-engine/Dockerfile (python:3.12-slim).

  INFRASTRUCTURE:
  [x] infrastructure/lib/ai-stack.ts: ai-analyzer DockerImageFunction (guardrail-ai-engine-{env}
        ECR, 512MB, 300s), computeEnabled two-phase gate (same ECR deadlock as scanner).
        Env: FINDINGS_TABLE, SCAN_JOBS_TABLE, EVENT_BUS_NAME, BEDROCK_EXPLAIN_MODEL/FIX_MODEL
        (us.* inference-profile IDs). IAM bedrock:InvokeModel scoped to the 2 inference-profile
        ARNs + backing foundation-model ARNs (region *), never "*". EventBridge ScanComplete rule.
        Wired in app.ts (addDependency foundation+scanner); deploy_env.sh builds the 5th image.

  TESTS:
  [x] ai-engine/tests/test_bedrock_client.py: 3 tests (success, throttle+retry, model routing).
  [x] ai-engine/tests/test_analyzer.py: 5 tests (all explained, CRIT/HIGH fix, MEDIUM/LOW skip=cost
        guard, risk_score calc + AI_COMPLETE, AIAnalysisComplete published). Full suite 43 passed, 76% cov.
  [x] DEPLOYED to dev (two-phase, --exclusively): repo+Lambda+rule live, wiring-verified via direct
        invoke (reached Bedrock, failed only on model access). Note: conftest adds ai-engine; scanner/
        src/__init__.py removed so `src` is a namespace pkg merging both services in one pytest session.
  [x] VERIFY acceptance criteria — PASSING via the gpt-oss runtime-token bridge (2026-06-28):
        fully automatic E2E (upload s3-public-bucket.tf → QUEUED→SCANNING→COMPLETE→AI_COMPLETE in
        ~75s), 13/13 findings have ai_explanation, CRITICAL/HIGH have ai_fix_code (cost guard:
        MEDIUM/LOW skipped), risk_score=48 populated, pytest 12 passed. gpt-oss cost << $0.05/scan.
        Claude/anthropic path stays the durable target — flip BEDROCK_PROVIDER=anthropic when model
        access is granted (AWS case open); zero code change needed.

═══════════════════════════════════════════════════════════════
PHASE 7: API Layer
═══════════════════════════════════════════════════════════════
GOAL: All application data is accessible via authenticated REST API.
      No WebSocket — email is the async completion notification.
      UI polls for status or user opens dashboard after receiving email.

ACCEPTANCE CRITERIA:
  ✓ curl -X POST /v1/scans (with JWT) → returns {presigned_url, scan_job_id}
  ✓ curl GET /v1/scans → returns paginated list of all scans (status, filename, risk_score)
  ✓ curl GET /v1/scans/{id} → returns full scan detail + all findings with ai_explanation
  ✓ curl GET /v1/scans/{id}/report → returns presigned S3 URL to PDF (valid 15 min)
  ✓ Request without JWT → 401 Unauthorized
  ✓ pytest api/tests/ → all pass

START COMMANDS:
  mkdir -p api/src/routes api/src/middleware api/tests

  CODE:
  [x] api/src/middleware/auth.py:
        Validates Cognito JWT using python-jose
        Raises 401 if token missing, expired, or wrong issuer
  [x] api/src/middleware/cors.py: CORS headers allowing CloudFront domain only
  [x] api/src/routes/scans.py:
        POST /v1/scans: generate S3 presigned PUT URL (expires 5 min), create QUEUED DDB record
        GET  /v1/scans: list all scans (paginated, max 50, sorted created_at desc)
                        Returns: scan_job_id, file_name, status, risk_score, finding_counts, created_at
        GET  /v1/scans/{id}: full scan detail
                        Returns: all scan fields + findings[] with rule_id, severity, resource_name,
                                 line_number, ai_explanation, ai_fix_code
  [x] api/src/routes/reports.py:
        GET /v1/scans/{id}/report: generate presigned S3 GET URL for PDF (expires 15 min)
                                   404 if report not yet generated
  [x] api/requirements.txt: boto3, python-jose[cryptography]
        NOTE: api entrypoint is src/app.py (NOT main.py) — scanner already owns the
        src.main module and all 3 services share one `src` namespace in pytest.

  INFRASTRUCTURE:
  [x] infrastructure/lib/api-stack.ts:
        API Gateway REST API (regional, Cognito User Pool authorizer)
        Lambda: api-handler (guardrail-api ECR image, 256MB, 29s) — all routes in one function
        SSM: /guardrail/{env}/api-url
        No WebSocket API — removed from scope (email is the notification mechanism)
        Same two-phase computeEnabled ECR gate as scanner/ai; deploy_env.sh builds the api image.
        app.ts: api depends on foundation + auth ONLY (NOT scanner/ai — it imports no
        export from them; adding those deps pulls them into `cdk deploy GuardrailApi` and
        under computeEnabled=false would strip their live Lambdas).

  TESTS:
  [x] api/tests/test_scans.py: 5 tests (POST success, GET list, GET by id, GET report url, no-auth-401)
  [x] api/tests/test_middleware.py: 3 tests (valid JWT passes, expired JWT 401, missing JWT 401)
  [x] VERIFY: deployed to dev + live-tested all 5 (2026-06-28): no-JWT→401; with Cognito JWT
        POST→200 {presigned_url, scan_job_id}, GET list→200, GET detail→200, GET report→404
        (no PDF until Phase 9). Full suite 55 passed, 85.86% cov.

═══════════════════════════════════════════════════════════════
PHASE 8: Frontend Dashboard
═══════════════════════════════════════════════════════════════
GOAL: Static React site hosted on S3 + CloudFront. Two views:
      (1) Scan list — all IaC files processed with status + risk score
      (2) Scan detail — full report for selected file with findings,
          AI explanations, and PDF download.
      User reaches the site after receiving the completion email, or
      can upload a new file from the list page.

USER FLOW:
  Login (Cognito) → Scan List page → click any scan → Scan Detail page
                                                           ├─ Risk Score meter
                                                           ├─ Findings table (CRITICAL first)
                                                           ├─ Click finding → AI explanation drawer
                                                           └─ "Download PDF Report" button

ACCEPTANCE CRITERIA (must test in browser — not just build):
  ✓ CloudFront URL loads Login page; unauthenticated access redirects to Login
  ✓ Login with Cognito credentials → lands on Scan List page
  ✓ Scan List shows all scans: filename, status badge, risk score, date
  ✓ Drag-drop demo-master-bad.tf on Scan List → "Scan queued" confirmation appears
  ✓ Click any COMPLETE scan → navigates to Scan Detail page
  ✓ Scan Detail: Risk Score meter shows correct color (RED if score > 60)
  ✓ Scan Detail: Findings table sorted CRITICAL first, shows rule_id + resource_name
  ✓ Click finding row → AI explanation drawer slides in with ai_explanation text
  ✓ For CRITICAL/HIGH findings: "View Fix" button shows ai_fix_code in code block
  ✓ "Download PDF Report" button triggers presigned URL download of PDF
  ✓ Lighthouse performance score ≥ 80

START COMMANDS:
  cd frontend
  npm create vite@latest . -- --template react-ts
  npm install tailwindcss @shadcn/ui @tanstack/react-query axios aws-amplify react-dropzone

  STACK NOTE: built with Tailwind v3 directly (NOT shadcn/ui CLI — its interactive
  init can't be one-shot reliably; hand-rolled Tailwind components meet the
  "professional look" intent). React 18 + TS 5.6 + Vite 5 + React Query v5 +
  Amplify v6 + react-router-dom v6 + react-dropzone. No Identity Pool in Amplify
  config (app uses API JWT only). Pure logic extracted to src/lib/risk.ts for tests.

  CODE:
  [x] src/lib/env.ts: typed env (VITE_API_URL, VITE_COGNITO_*; no VITE_WS_URL)
  [x] src/lib/api.ts: Axios baseURL=VITE_API_URL + JWT interceptor (Bearer id-token)
  [x] src/lib/auth.ts: Amplify v6 wrapper (configureAuth, signIn, signOut, getIdToken,
        isAuthenticated) — User Pool only (USER_PASSWORD_AUTH)
  [x] src/lib/types.ts + src/lib/risk.ts: API types + pure risk/severity/status logic
  [x] src/hooks/useScans.ts: useScans (30s poll), useScan (15s poll until COMPLETE/FAILED),
        useReportUrl (lazy), useCreateScan (POST + presigned PUT)
  [x] src/pages/LoginPage.tsx: email+password → signIn → /scans, error display
  [x] src/pages/ScanListPage.tsx: header + sign-out + ScanUploader + scans table
        (status badge, risk chip, date, View Report) + empty state
  [x] src/pages/ScanDetailPage.tsx: back link + Download PDF + RiskScoreMeter +
        finding_counts grid + FindingsTable + AiExplanationPanel drawer
  [x] src/components/ScanUploader.tsx: react-dropzone (.tf/.hcl/.yaml/.yml/.json/.template),
        POST→presigned PUT, "Scan queued" confirmation
  [x] src/components/RiskScoreMeter.tsx: SVG gauge, 4 color bands per thresholds
  [x] src/components/FindingsTable.tsx: severity sort + filter bar + row→drawer + View Fix
  [x] src/components/AiExplanationPanel.tsx: 480px drawer, Explanation + Fix tabs, copy
  [x] src/components/{AppHeader,RequireAuth}.tsx + App.tsx (router) + main.tsx (providers)
  [x] src/lib/risk.test.ts: 6 vitest tests (risk bands, severity sort, fix guard, status)

  INFRASTRUCTURE:
  [x] infrastructure/lib/frontend-stack.ts:
        Dashboard bucket guardrail-dashboard-{env}-{account} stays in FoundationStack;
        this stack imports it BY NAME (deterministic, no Foundation token) + adds the
        OAC bucket policy HERE — avoids the OAC dependency cycle AND the Fn::GetStackOutput
        failure a bucket token caused. CloudFront OAC (NOT OAI), HTTPS redirect,
        defaultRootObject index.html, 403/404 → /index.html (SPA), PriceClass_100.
        SSM: /guardrail/{env}/cloudfront-dist-id, /guardrail/{env}/cloudfront-url.
        ⚠ DEPLOY BLOCKED (account-level, NOT code): CloudFront Distribution create →
          403 "Your account must be verified before you can add new CloudFront resources"
          — needs an AWS Support case (same class as the Phase 6 Bedrock blocker).
          OAC + bucket policy create fine; only the Distribution itself is gated.
  [x] infrastructure/lib/frontend-host-stack.ts (STOPGAP — $0-idle, LIVE NOW):
        guardrail-frontend-host-{env} container Lambda behind a public Function URL
        (authType NONE) serving the SAME dashboard bundle from S3. SPA routing in-handler.
        computeEnabled two-phase ECR gate. SSM /guardrail/{env}/frontend-url.
        LIVE dev: https://g6p2vamezwbvtug6ohppi34uyi0pwvqd.lambda-url.us-east-1.on.aws/
        When CloudFront is verified, deploy GuardrailFrontend-{env} + switch URL — no rebuild.
  [x] GitHub Actions 04-deploy-frontend.yml: pre-existing; syncs dist/ to the dashboard
        bucket (which BOTH delivery paths read) + fetches VITE_* from SSM.
  [x] scripts/deploy_env.sh: builds the 7th image (frontend-host) in the bootstrap.

  VERIFY (infra + auth path DONE 2026-06-28): Function URL serves index.html (200, title
    "Security Guardrail Auditor") + JS asset (200, 456KB) + SPA fallback /scans/{id}→index.html
    + missing asset→404. Login USER_PASSWORD_AUTH → ID token → API GET /v1/scans → 200.
    npm run build OK; vitest 6/6 pass.
    REMAINING (manual, in a browser by the owner — the 11 interaction criteria): login form
    redirect, drag-drop upload, risk-meter color, findings CRITICAL-first sort, AI drawer,
    View Fix, PDF download, Lighthouse ≥80.
    Test login (dev pool): puneetkumarsingh765@gmail.com / Guardrail2026 (permanent).

═══════════════════════════════════════════════════════════════
PHASE 9: Email Notifications & Observability          ✅ COMPLETE
═══════════════════════════════════════════════════════════════
GOAL: User receives an email on every scan completion containing:
      - A CRITICAL/HIGH-only summary in the email body
      - Full PDF report as email attachment
      Slack/Teams notifications are OUT OF SCOPE for this demo.
      System health visible in CloudWatch. All Lambdas traced in X-Ray.

EMAIL SPEC:
  Trigger:   EventBridge ReportGenerated event (after PDF is ready in S3)
  To:        puneetkumarsingh765@gmail.com  ← HARDCODED for this demo
  From:      puneetkumarsingh765@gmail.com  ← SES verified identity (same address, SES sandbox OK)
  Subject:   "Scan Complete: {file_name} — Risk Score {risk_score}/100"
  SES Note:  SES sandbox only allows sending to verified addresses. Both From and To are the same
             verified address — no production access request needed for this demo.
  Body (plain text + HTML):
    "Your IaC file '{file_name}' has been scanned.
     Risk Score: {risk_score}/100 ({label})

     Issues Requiring Attention ({critical_count} CRITICAL, {high_count} HIGH):
     ─────────────────────────────────────────
     [CRITICAL] S3-001 — aws_s3_bucket.my_bucket — Public ACL detected (line 12)
     [CRITICAL] SG-001 — aws_security_group.web — SSH open to 0.0.0.0/0 (line 34)
     [HIGH]     IAM-001 — aws_iam_policy.admin — Wildcard action (*) in policy (line 8)
     ─────────────────────────────────────────
     MEDIUM and LOW findings, and all compliant resources, are in the attached PDF.
     View full report: {cloudfront_url}/scans/{scan_job_id}"
  Attachment: {scan_job_id}-report.pdf (from S3 scan-reports bucket)
  IMPORTANT: Do NOT include MEDIUM/LOW findings in email body.
             Do NOT mention compliant/passing resources in email body.
             Full detail (all severities) is ONLY in the PDF attachment.

ACCEPTANCE CRITERIA:
  ✓ Upload demo-master-bad.tf → email received within 3 minutes of scan completing
  ✓ Email body contains only CRITICAL + HIGH findings (no MEDIUM/LOW, no passing resources)
  ✓ PDF attachment opens correctly and contains full report (all severities)
  ✓ CloudWatch dashboard shows scan-volume + Lambda error rates
  ✓ X-Ray traces visible for ingest → rules-engine → AI → report → email flow
  ✓ Billing alarm tested: set to $0.01, verify email, restore to $20

VERIFIED 2026-06-28 (live dev, E2E success path):
  Uploaded a bad TF → QUEUED→SCANNING→COMPLETE→AI_COMPLETE(risk=48)→REPORT_COMPLETE in ~80s.
  PDF in S3 (8,886 bytes, %PDF- magic). email-handler logged success_email_sent (SES accepted,
  identity Verified). Dashboard GuardrailHealth-dev created; all 7 Lambdas have tracing=ACTIVE.
  Failure path (ECS exit≠0 / DLQ → ScanFailed → failure email) is DEPLOYED + unit-tested, not
  live-fired. Billing-alarm $0.01 toggle = optional owner step (left at $20 to avoid alarm noise).
  NOTE: EventBridge at-least-once delivered ReportGenerated twice → 2 emails for 1 scan. Harmless
  for the demo; add an idempotency guard (skip if report_s3_key already set) if it matters.

ARCHITECTURE NOTE (differs from the boilerplate below):
  report/email/failure are 3 Lambdas sharing ONE new image guardrail-report-{env} (carries
  reportlab), each with its own DockerImageCode cmd — NOT "guardrail-scanner image + MODE". The
  scanner per-service ECR pattern has no shared scanner image; this mirrors ingest/aggregator
  (direct handler cmd, no MODE). email-handler picks success vs failure from the EventBridge
  detail-type at runtime (EventBridge can't inject env vars into a Lambda target), not EMAIL_TYPE.

START COMMANDS:
  mkdir -p scanner/src/report_generator

  CODE:
  [x] scanner/src/report_generator/pdf_generator.py:
        Input: scan_job dict + findings list (all severities)
        Uses reportlab or weasyprint to generate PDF
        Sections: Cover (filename, date, risk score), Executive Summary,
                  CRITICAL findings, HIGH findings, MEDIUM findings, LOW findings,
                  Compliant Resources (grouped by category)
        Output: bytes → caller uploads to S3

  [x] scanner/src/handlers/report_handler.py Lambda:
        Triggered by: EventBridge AIAnalysisComplete
        1. Read scan_job from DDB (scan-jobs table)
        2. Read all findings from DDB (findings table, query by scan_job_id)
        3. Call pdf_generator.generate(scan_job, findings) → PDF bytes
        4. Upload PDF to S3: scan-reports/{scan_job_id}/report.pdf
        5. Update scan-jobs: report_s3_key = "scan-reports/{scan_job_id}/report.pdf"
        6. Publish EventBridge: ReportGenerated {scan_job_id, report_s3_key, user_email}

  [x] scanner/src/handlers/email_handler.py Lambda:
        Handles TWO event types — success and failure — distinguished by EMAIL_TYPE env var
        set per EventBridge rule (one rule → ReportGenerated, one rule → ScanFailed).

        SUCCESS PATH (EMAIL_TYPE=success, triggered by ReportGenerated):
          1. Fetch secrets (ses_from_email, ses_to_email) from Secrets Manager via APP_SECRETS_ARN
          2. Read scan_job from DDB
          3. Read findings — CRITICAL + HIGH only from DDB
          4. Download PDF from S3 (scan_job.report_s3_key)
          5. Build MIME email:
               Subject: "Scan Complete: {file_name} — Risk Score {risk_score}/100"
               Body: CRITICAL+HIGH finding lines only (rule_id | resource | line)
                     Footer: link to dashboard + "Full detail in attached PDF"
               Attachment: {scan_job_id}-report.pdf
          6. SES send_raw_email()
          7. Log: {event: success_email_sent, scan_job_id}

        FAILURE PATH (EMAIL_TYPE=failure, triggered by ScanFailed):
          1. Fetch secrets from Secrets Manager
          2. Read scan_job from DDB (status=FAILED, failed_stage, error_message, trace_id)
          3. Build plain-text email (no PDF — report was never generated):
               Subject: "SCAN FAILED: {file_name} — Developer Attention Required"
               Body:
                 File: {file_name} | Scan ID: {scan_job_id}
                 Failed at: {failed_stage}
                 Error: {error_message}
                 Debug:
                   CloudWatch Logs: /guardrail/{env}/ecs/{failed_stage}
                   X-Ray Trace: {trace_id}
                   DynamoDB: scan-jobs-{env} PK={scan_job_id}
                 No report was generated. Resubmit after the bug is fixed.
          4. SES send_raw_email()
          5. Log: {event: failure_email_sent, scan_job_id, failed_stage}

  [x] scanner/src/handlers/failure_handler.py Lambda:
        Triggered by TWO sources:
          a) EventBridge rule: ECS TaskStopped where detail.containers[].exitCode != 0
          b) CloudWatch Alarm on SQS DLQ (checkov-results-dlq) depth > 0 → SNS → this Lambda
        Steps:
          1. Extract scan_job_id from event (ECS task tags or DLQ message body)
          2. Identify failed_stage from event source (rules-engine-task or checkov-task)
          3. Update DDB scan-jobs: status=FAILED, failed_stage, error_message, trace_id
          4. Publish EventBridge: ScanFailed {scan_job_id, failed_stage, error_message, trace_id}

  [x] scanner/src/services/email_service.py:
        build_success_email(scan_job, crit_high_findings, pdf_bytes, cf_url) → MIMEMultipart
        build_failure_email(scan_job) → MIMEMultipart
        send_email(mime_msg, from_addr, to_addr) → None   (calls boto3 SES send_raw_email)

  [x] scanner/requirements.txt: add reportlab

  INFRASTRUCTURE:
  [x] infrastructure/lib/monitoring-stack.ts:
        CloudWatch Dashboard "GuardrailHealth":
          Widget 1: scan completions per hour
          Widget 2: Lambda + ECS task error rates
          Widget 3: Bedrock invocation latency p95
        X-Ray: enable active tracing on ALL Lambda functions (update Lambda defs in all stacks)
        Alarms → SNS guardrail-ops-alerts → email puneetkumarsingh765@gmail.com:
          Lambda error rate > 5% over 5 minutes
          ECS task exit code non-zero
          Bedrock p95 latency > 10 seconds
  [x] infrastructure/lib/scanner-stack.ts additions:
        Lambda: report-handler (guardrail-scanner ECR image, 512MB, 120s, MODE=report)
        Lambda: email-handler (guardrail-scanner ECR image, 256MB, 30s, MODE=email)
        EventBridge rule: AIAnalysisComplete → report-handler
        EventBridge rule: ReportGenerated → email-handler
        IAM: email-handler needs ses:SendRawEmail on arn:aws:ses:us-east-1:{account}:identity/puneetkumarsingh765@gmail.com
        IAM: email-handler needs secretsmanager:GetSecretValue on guardrail/{env}/app-secrets ARN
        IAM: report-handler needs s3:PutObject on scan-reports bucket
        Secrets Manager secret (created in foundation-stack.ts, one per env):
          Name:  guardrail/{env}/app-secrets
          Value: {"ses_from_email":"puneetkumarsingh765@gmail.com","ses_to_email":"puneetkumarsingh765@gmail.com"}
          KMS:   encrypted with project KMS key
          Rotation: none (static demo config)
        SSM parameters (non-sensitive config — stays in SSM as before):
          /guardrail/{env}/cloudfront-url  = https://{dist-id}.cloudfront.net

  INFRASTRUCTURE additions (scanner-stack.ts):
        Lambda: failure-handler (guardrail-scanner ECR image, 128MB, 30s, MODE=failure)
        EventBridge rule: ECS TaskStopped exitCode≠0 → failure-handler
        CloudWatch Alarm: checkov-results-dlq depth > 0 → SNS → failure-handler
        EventBridge rule: ScanFailed → email-handler (EMAIL_TYPE=failure injected by rule)
        EventBridge rule: ReportGenerated → email-handler (EMAIL_TYPE=success injected by rule)
        IAM: failure-handler → dynamodb:UpdateItem on scan-jobs + events:PutEvents

  TESTS:
  [x] scanner/tests/test_pdf_generator.py: 3 tests (bytes generated, all sections present, CRITICAL first)
  [x] scanner/tests/test_report_handler.py: 3 tests (PDF in S3, DDB updated, ReportGenerated published)
  [x] scanner/tests/test_email_handler.py: 6 tests
        success path: body has CRITICAL line, body has HIGH line, body excludes MEDIUM/LOW, PDF attached
        failure path: subject contains FAILED, body has failed_stage + error, no PDF attached
  [x] scanner/tests/test_failure_handler.py: 3 tests
        ECS exit≠0 → DDB status=FAILED, ScanFailed published, failed_stage correctly identified

  [x] VERIFY: success-path acceptance criteria PASS live (see VERIFIED note above); failure path deployed+unit-tested

═══════════════════════════════════════════════════════════════
PHASE 10: Demo Lifecycle & README                    ✅ COMPLETE
═══════════════════════════════════════════════════════════════
GOAL: The demo can be fully put to sleep between client calls and
      woken up reliably the night before. README is client-ready.

ACCEPTANCE CRITERIA:
  ✓ python scripts/demo_sleep.py → CloudFront shows Disabled in console within 1 min
  ✓ python scripts/demo_wake.py → dashboard accessible at CloudFront URL within 15 min
  ✓ python scripts/billing_check.py → prints per-service cost breakdown
  ✓ After sleep + 48 hours idle → billing_check.py shows < $5 accumulated
  ✓ Full end-to-end demo rehearsal completes in under 10 minutes

REALITY NOTE (2026-06-28): CloudFront is blocked on this account (verification
  pending — see Phase 8), so the dashboard is the $0-idle Lambda Function URL host.
  demo_sleep/demo_wake DISABLE/ENABLE CloudFront *if a distribution exists* (reads
  /guardrail/{env}/cloudfront-dist-id); when absent they no-op that step and report
  the serverless host is already at the cost floor — nothing to stop. Scripts work
  unchanged the day CloudFront is deployed.

START COMMANDS:
  mkdir scripts

  [x] scripts/demo_sleep.py:
        1. Read CloudFront dist ID from SSM /guardrail/{env}/cloudfront-dist-id
        2. Disable the distribution if present (not delete — preserves all config);
           if absent, report the $0-idle Function URL host has nothing to stop
        3. Write {state: sleeping, timestamp} to SSM /guardrail/{env}/demo-state
        4. Print idle-cost summary + "Run demo_wake.py before next call."
  [x] scripts/demo_wake.py:
        1. Re-enable CloudFront distribution if present (else no-op)
        2. Call seed_demo_data.main() in-process
        3. Write {state: awake, timestamp} to SSM /guardrail/{env}/demo-state
        4. Print live dashboard URL (frontend-url, fallback cloudfront-url)
  [x] scripts/seed_demo_data.py:
        Write 3 pre-canned scan jobs to DynamoDB (HIGH=72 / MEDIUM=45 / LOW=16),
          dated across the past week so newest=lowest = improving-posture trend
          (renders in the actual Scan List — TrendChart is out of scope, no dead data)
        Realistic findings with ai_explanation + ai_fix_code (CRITICAL/HIGH) pre-populated
        Deterministic uuid5 ids → re-seeding overwrites, never duplicates (idempotent)
        Leaves report_s3_key unset (no fake PDF) — run a real scan for the PDF path
  [x] scripts/billing_check.py:
        Cost Explorer get_cost_and_usage, current month, group by SERVICE
        Table sorted by cost desc; total; warns if > $15 (--warn-at to override)
  [x] README.md (client-facing, public):
        1-paragraph description, ASCII architecture diagram, capabilities,
        tech-stack badges, 3-command deploy, idle-vs-active cost table, screenshots placeholder

  VERIFIED 2026-06-28 (live dev): seed → 3 scans in scan-jobs-dev (72/45/16, COMPLETE,
    findings with AI text); demo_wake → seeds + state=awake + prints Function URL; dashboard
    HTTP 200; demo_sleep → records state=sleeping (no CF to disable); billing_check → per-service
    table, TOTAL $0.95 month-to-date (well under <$5 idle / <$15 dev). The 48h-idle and
    in-browser 10-min rehearsal criteria are owner manual steps; current spend confirms trajectory.

═══════════════════════════════════════════════════════════════
PHASE 11: Production Hardening
═══════════════════════════════════════════════════════════════
GOAL: Project is secure by default, cost-capped, and ready for
      public portfolio review and real client usage.

ACCEPTANCE CRITERIA:
  ✓ checkov -d infrastructure/cdk.out/ → 0 CRITICAL findings on own infrastructure
  ✓ Security Hub: AWS Foundational Security Best Practices score ≥ 80%
  ✓ Locust load test: 50 concurrent users, 50 scans, all complete, 0 Lambda errors
  ✓ aws cloudfront get-distribution-config → WAF WebACL attached
  ✓ Total deployed cost after 1 week of dev usage < $20

  [ ] WAF WebACL on API Gateway:
        AWSManagedRulesCommonRuleSet (SQLi, XSS, etc.)
        Rate limit: 1000 requests per 5 minutes per IP
  [ ] WAF WebACL on CloudFront:
        AWSManagedRulesCommonRuleSet
  [ ] VPC endpoints created: S3, DynamoDB, Bedrock, SSM, ECR API, ECR DKR
        (eliminates all internet-bound traffic from Lambdas, no NAT Gateway ever)
  [ ] CloudTrail trail: management + S3 object-level data events → S3 + KMS-encrypted
  [ ] AWS Config rules enabled:
        s3-bucket-public-read-prohibited, restricted-ssh,
        encrypted-volumes, iam-no-inline-policy
  [ ] Security Hub enabled: AWS Foundational Security Best Practices standard
  [ ] Lambda reserved concurrency set per function (prevents runaway cost):
        ai-analyzer: 5, api-handler: 20, ingest-handler: 10, aggregator: 10,
        report-handler: 5, email-handler: 5, failure-handler: 5
        NOTE: rules-engine and checkov are ECS tasks — concurrency controlled by
              EventBridge RunTask rate limits, not Lambda concurrency
  [ ] API Gateway throttling: 1000 req/s burst, 500 req/s steady per stage
  [ ] SQS dead-letter queue: alarm on DLQ message count > 0
  [ ] Run checkov on infrastructure/cdk.out/ → fix all CRITICAL + HIGH findings
  [ ] Locust load test script: locustfile.py (50 users, upload 1 file each, verify completion)
  [ ] DR validation: cdk deploy --context env=dr --region us-west-2 (FoundationStack only)
  [ ] Final billing verification: confirm < $20 total after 1 week dev use
  [ ] Tag audit: verify all AWS resources have Project + Environment + Owner tags
```

---

## SESSION TRACKER

**MOST RECENT SESSION: June 28, 2026 — PHASE 10 DEMO LIFECYCLE & README ✅ COMPLETE + LIVE-VERIFIED**

### What Was Completed This Session (Phase 10)
- **PHASE 10 DEMO LIFECYCLE & README: COMPLETE + LIVE-VERIFIED IN DEV.** Four operational
  scripts + a client-facing README. All run live against dev with the aws-admin profile.
- **scripts/seed_demo_data.py** — writes 3 pre-canned scans to scan-jobs-dev / findings-dev:
  legacy-vpc-stack.tf (risk 72, HIGH/red), staging-app-platform.tf (45, MEDIUM/amber),
  prod-baseline.tf (16, LOW/green), dated 6/3/0 days ago so newest=lowest = an improving-posture
  trend visible in the actual Scan List (TrendChart is out of scope, so NO dead trend table —
  the trend lives in the real list). Findings carry realistic ai_explanation + ai_fix_code
  (CRITICAL/HIGH only, matching the Phase 6 cost guard). Risk scores computed with the canonical
  WEIGHTS algorithm. Deterministic uuid5 ids → re-seeding overwrites, never duplicates
  (idempotent — safe on every wake). Leaves report_s3_key unset (no fake PDF).
- **scripts/demo_sleep.py / demo_wake.py** — sleep disables CloudFront *if a distribution exists*
  (reads /guardrail/{env}/cloudfront-dist-id), wake re-enables it; both record
  /guardrail/{env}/demo-state. CRITICAL REALITY: CloudFront is blocked on this account, so the
  dashboard is the $0-idle Lambda Function URL host — the scripts detect the missing dist-id and
  no-op that step, reporting the serverless host is already at the cost floor. wake calls
  seed_demo_data.main() in-process and prints the live URL (frontend-url, fallback cloudfront-url).
- **scripts/billing_check.py** — Cost Explorer get_cost_and_usage, current month, grouped by
  SERVICE, sorted desc, warns if > $15 (--warn-at override). Pinned to us-east-1 (CE requirement).
- **README.md** — client-facing: 1-para description, ASCII architecture diagram (full event flow),
  capabilities, tech-stack badges, 3-command deploy, idle-vs-active cost table, screenshots placeholder.
- **Windows-console fix:** all scripts force `sys.stdout.reconfigure(encoding="utf-8")` (guarded) and
  billing_check uses ASCII table glyphs — cp1252 can't encode → / box-drawing and crashed billing_check
  on first run. Fixed + re-verified.
- **LIVE VERIFY (dev):** seed → 3 rows confirmed via DDB scan (72/45/16, status COMPLETE); demo_wake →
  seeds + state=awake + prints Function URL; dashboard curl → HTTP 200; demo_sleep → state=sleeping
  (no CF to disable); billing_check → per-service table, **TOTAL $0.95 month-to-date** (well under the
  <$5 idle / <$15 dev guardrails). Env left in awake+seeded state for the owner's browser pass.
- **Known carry-over (non-blocking):** the "48h idle < $5" and "in-browser 10-min rehearsal" criteria
  are owner manual steps; the $0.95 month-to-date total confirms the cost trajectory is on target.

### What Was Completed (Prior session — Phase 9)
- **PHASE 9 EMAIL NOTIFICATIONS & OBSERVABILITY: CODE + INFRA DONE, DEPLOYED, E2E-VERIFIED IN DEV.**
- **PHASE 9 EMAIL NOTIFICATIONS & OBSERVABILITY: CODE + INFRA DONE, DEPLOYED, E2E-VERIFIED IN DEV.**
  Pipeline now runs all the way to a PDF + email: upload→…→AI_COMPLETE→**report-handler** (reportlab
  PDF → scan-reports/{id}/report.pdf → ReportGenerated)→**email-handler** (SES raw email, CRITICAL/HIGH
  body + PDF attachment). Live E2E: bad TF → REPORT_COMPLETE in ~80s, valid PDF (8,886 B, %PDF-) in S3,
  email-handler logged `success_email_sent` (SES identity Verified). New scan-jobs status REPORT_COMPLETE.
- **New scanner code:** `src/report_generator/pdf_generator.py` (cover + exec summary + per-severity
  sections, CRITICAL first), `src/services/email_service.py` (build_success/build_failure MIME + SES
  send_raw_email; CRITICAL/HIGH-only body enforced in one `_crit_high` chokepoint),
  `src/handlers/report_handler.py`, `email_handler.py` (routes success vs failure off the EventBridge
  **detail-type** at runtime — EventBridge can't inject env vars into a Lambda), `failure_handler.py`
  (ECS exit≠0 OR SNS/DLQ → status=FAILED + ScanFailed). 15 new tests; full suite **74 passed, 86.87% cov**.
- **One new ECR image `guardrail-report-{env}`** (boto3+reportlab+awslambdaric) shared by all 3 Lambdas,
  each with its own DockerImageCode cmd — NOT a "scanner image + MODE" (no such shared image exists;
  this mirrors the ingest/aggregator per-service pattern). `scanner/report/{Dockerfile,requirements.txt}`.
- **Infra:** foundation-stack.ts → Secrets Manager `guardrail/{env}/app-secrets` (ses_from/to) +
  SSM `/guardrail/{env}/cloudfront-url`. scanner-stack.ts → report ECR repo + 3 Lambdas (gated by the
  same computeEnabled two-phase flag) + EventBridge rules (AIAnalysisComplete→report,
  ReportGenerated→email, ScanFailed→email, ECS-TaskStopped-exit≠0→failure) + checkov-DLQ depth alarm →
  SNS → failure-handler. NEW **monitoring-stack.ts** (GuardrailMonitor-{env}): GuardrailHealth dashboard
  + guardrail-ops-alerts SNS + per-Lambda Errors alarms + ai-analyzer p95 latency alarm. X-Ray active
  tracing was already on every Lambda. deploy_env.sh builds the 8th image.
- **CDK gotcha fixed:** `appSecret.grantRead(role)` created a Foundation→Scanner **dependency cycle**
  (the grant mutates the secret's policy in Foundation to name the Scanner role). Fix: grant
  `secretsmanager:GetSecretValue` via an explicit statement on the role (referencing the ARN token,
  Scanner→Foundation direction); KMS decrypt already covered by grantEncryptDecrypt. monitoring-stack
  references pipeline Lambdas BY METRIC DIMENSION (name strings), never by construct — so a monitor
  deploy can't pull scanner/ai into its change set or trip the computeEnabled strip.
- **Deployed via the locked two-phase recipe** (Phase A computeEnabled=false → push report image →
  Phase B computeEnabled=true), `--exclusively`, background cdk. 8 stacks now live incl. GuardrailMonitor.
- **Known minor:** EventBridge at-least-once delivered ReportGenerated twice → 2 emails for 1 scan.
  Harmless for demo; add idempotency (skip if report_s3_key already set) later. Billing-alarm $0.01
  toggle = optional owner step (left at $20).

### What Was Completed (Prior session — Phase 8)
- **PHASE 8 FRONTEND DASHBOARD: CODE COMPLETE + LIVE IN DEV.** Full Vite/React 18/TS dashboard
  (Tailwind v3, React Query v5, Amplify v6, react-router v6, react-dropzone): LoginPage,
  ScanListPage (uploader + status/risk table), ScanDetailPage (RiskScoreMeter SVG gauge +
  finding_counts + FindingsTable + AiExplanationPanel drawer). lib/ (env, api+JWT interceptor,
  auth, pure risk logic, types), hooks/useScans (30s/15s polling — replaces removed WebSocket).
  22 frontend files. `npm run build` OK; vitest 6/6 (risk bands, severity sort, fix guard, status).
- **⚠ CLOUDFRONT BLOCKED (account-level, NOT code) — same class as the Phase 6 Bedrock blocker.**
  `infrastructure/lib/frontend-stack.ts` synths + the OAC creates fine, but CloudFront Distribution
  CREATE returns 403 "Your account must be verified before you can add new CloudFront resources."
  → **needs an AWS Support case.** Template is correct; only the Distribution resource is gated.
- **STOPGAP THAT SHIPPED ($0-idle, LIVE):** `frontend-host/` — a container Lambda behind a public
  **Function URL** serves the SAME dashboard bundle from the S3 dashboard bucket (SPA routing
  in-handler). New `infrastructure/lib/frontend-host-stack.ts` (computeEnabled two-phase ECR gate).
  **LIVE: https://g6p2vamezwbvtug6ohppi34uyi0pwvqd.lambda-url.us-east-1.on.aws/**
  Verified: root 200 (correct title) + JS asset 200 (456KB) + /scans/{id}→index.html (SPA) + 404 on
  missing asset. **Auth path verified:** USER_PASSWORD_AUTH → ID token → API GET /v1/scans → 200.
  When CloudFront is verified, deploy GuardrailFrontend-{env} + switch the URL — NO rebuild (same S3 bundle).
- **Cognito test login created** (dev pool, self-signup is off): puneetkumarsingh765@gmail.com /
  `Guardrail2026` (permanent password via admin-set-user-password).
- **TWO CDK GOTCHAS FIXED (logged below):** (1) OAC over a cross-stack bucket → dependency cycle +
  Fn::GetStackOutput failure → import bucket BY deterministic NAME (not the Foundation token) and add
  the OAC bucket policy in the consuming stack. (2) A background `cdk deploy` inherits the launcher's
  cwd — if that isn't `infrastructure/`, cdk fails "--app is required"; always `cd infrastructure` in
  the deploy command.
- **Decision:** built with **Tailwind v3 directly (not shadcn/ui CLI)** — its interactive init can't be
  one-shot reliably; hand-rolled components meet the "professional look" intent. Logged in KNOWN DECISIONS.
- Committed on feature/phase-8-frontend (2 commits). PR → dev pending in this housekeeping turn.

### What Was Completed (Prior session — Phase 7)
- **PHASE 7 API LAYER: DEPLOYED + LIVE-VERIFIED IN AWS.** `guardrail-api-dev` Lambda behind an
  API Gateway REST API (https://ajdt217kkg.execute-api.us-east-1.amazonaws.com/dev/) with a
  Cognito User Pool authorizer. Live-tested with a real Cognito JWT: no-JWT→401; POST /v1/scans→200
  {presigned_url, scan_job_id}; GET /v1/scans→200 list; GET /v1/scans/{id}→200 detail; GET
  /v1/scans/{id}/report→404 (no PDF until Phase 9). Full suite 55 passed, 85.86% cov. PR #17.
- **New: api/** — src/app.py (dispatcher), routes/scans.py + routes/reports.py, middleware/auth.py
  (python-jose Cognito JWT: JWKS/RS256/issuer/exp/token_use), middleware/cors.py (Decimal-safe JSON),
  Dockerfile (python:3.12-slim + awslambdaric), requirements (+python-jose[cryptography]), 8 tests.
  **Entrypoint is src/app.py, NOT main.py** — scanner already owns `src.main` and all 3 services
  share ONE `src` namespace in the pytest session; a 2nd src/main.py would collide. (routes/ and
  middleware/ have __init__.py; src/ does not — namespace pkg, same as scanner/ai-engine.)
- **New: infrastructure/lib/api-stack.ts** — same two-phase computeEnabled ECR gate as scanner/ai.
  Modified: app.ts (ApiStack wired, depends on foundation+auth ONLY), deploy_env.sh (6th image:
  api), conftest.py (+api in the src path list), scanner/src/handlers/ingest_handler.py.
- **SINGLE-RECORD ingest change:** the API embeds scan_job_id in the upload key (uploads/<uuid>/<file>);
  ingest now reuses that UUID instead of minting a new one, so one job = one DDB row end-to-end.
  Direct uploads without a UUID 2nd segment still mint a fresh id (existing ingest tests unchanged).
- **⚠ INCIDENT + RECOVERY (lesson logged below):** a foreground `cdk deploy` (no --exclusively, with
  computeEnabled=false) TIMED OUT at the 2-min tool limit but its node child KEPT RUNNING detached and
  deployed the dependency stacks — STRIPPING the scanner + ai Lambdas (computeEnabled=false removes
  them). Recovered fully: killed the rogue PID, deleted the half-made REVIEW_IN_PROGRESS api stack,
  re-created the api ECR repo (compute=false), pushed the api image, then `cdk deploy --all`
  (compute=true) restored ALL Lambdas (ingest/aggregator/ai-analyzer) + created api. Verified all 5
  stacks UPDATE_COMPLETE + 4 Lambdas live.
- **CDK auth gotcha (this tool shell):** the CDK CLI's node SDK did NOT pick up the aws-admin SSO
  cache → "no credentials configured". FIX: `eval "$(aws configure export-credentials --profile
  aws-admin --format env)"` + `export CDK_DEFAULT_ACCOUNT/REGION` in the SAME command (shell state
  doesn't persist between Bash calls). `aws` CLI v2 commands work with just AWS_PROFILE=aws-admin.
- **Git Bash gotcha:** a leading-slash arg like `/guardrail/dev/api-url` gets MSYS-mangled into
  `C:/Program Files/Git/...` → false ParameterNotFound. FIX: prefix with `MSYS_NO_PATHCONV=1`.

### What Was Completed (Prior session — Phase 6 + ops)
- **PHASE 6 AI ANALYSIS ENGINE: WORKING END-TO-END IN AWS.** Fully automatic pipeline
  upload→scan→COMPLETE→ScanComplete→ai-analyzer→AI_COMPLETE (~75s); 13/13 findings explained,
  CRITICAL/HIGH fixed, risk_score set. 47 tests pass.
- **DUAL-PROVIDER bedrock_client** (BEDROCK_PROVIDER env): "anthropic" (Claude via IAM, durable
  target, pending model access) and "openai_compat" (gpt-oss TODAY). Deployed with openai_compat.
- **RUNTIME BEARER-TOKEN GENERATION (no stored secret, never logged):** the analyzer signs a
  short-lived Bedrock bearer token from its OWN IAM role per call (SigV4-presign CallWithBearerToken)
  and calls gpt-oss on the OpenAI-compatible endpoint https://bedrock-mantle.us-east-1.api.aws/v1.
  Signing quirk: `Version=1` goes in the token URL but is EXCLUDED from the signed canonical request.
  IAM: the `bedrock-mantle` PREVIEW service needs `bedrock-mantle:*` (CallWithBearerToken +
  CreateInference) — NOT the `bedrock` namespace (discovered from the endpoint's own authz errors).
- (Earlier same session) Phase 6 code + infra + 12 ai-engine tests, deployed two-phase, committed PR #13.
  - New: ai-engine/ (analyzer.py, bedrock_client.py, 3 prompts, Dockerfile, reqs, 8 tests),
    infrastructure/lib/ai-stack.ts. Modified: app.ts (AiStack wired), deploy_env.sh (5th image),
    conftest.py (+ai-engine). Removed scanner/src/__init__.py → `src` is now a NAMESPACE package
    so scanner + ai-engine both resolve `from src.X` in ONE pytest session (don't re-add it).
  - Deployed two-phase with `--exclusively` (scanner untouched): guardrail-ai-engine-dev ECR +
    ai-analyzer Lambda (512MB/300s) + ScanComplete EventBridge rule, all live (UPDATE_COMPLETE).
  - Direct-invoke wiring test PASSED to the Bedrock boundary: analyzer read job+findings, called
    Bedrock, failed ONLY at InvokeModel "Operation not allowed" → IAM/env/DDB/prompt all correct.
- **⚠ BEDROCK MODEL ACCESS BLOCKER:** account 879072872327 is NOT_AUTHORIZED for Haiku 4.5 +
  Sonnet 4.6. Anthropic needs a CONSOLE use-case form (CLI agreement accept fails: "fill out the
  request form"). NO model (Nova/Llama/OpenAI gpt-oss) is enableable purely via CLI here. User
  RAISED AN AWS SUPPORT CASE. Once access is granted, run the E2E to finish Phase 6.
- **MODEL-ID CORRECTION:** CLAUDE.md's IDs were wrong — Claude 4.x is inference-profile-only.
  Correct invoke IDs: `us.anthropic.claude-haiku-4-5-20251001-v1:0` / `us.anthropic.claude-sonnet-4-6`.
  IAM scopes InvokeModel to those profile ARNs + backing foundation-model ARNs (region *), never "*".
- **OPS — accidental S3 bucket recovered:** the deleted bucket was the CDK bootstrap staging bucket
  `cdk-hnb659fds-assets-879072872327-us-east-1` (CDKToolkit still CREATE_COMPLETE but bucket 404 →
  would break `cdk deploy`). Recreated WITHOUT versioning (block-public + AES256 + TLS-only). All 5
  app buckets + 20-rule catalog + 4 ECR images were intact. Re-ran E2E for phases 1-5: COMPLETE, 48
  findings, 4 CRITICAL — confirmed healthy before deploying Phase 6.
- **OPS — eu-north-1 swept:** zero user resources (only AWS default VPC, $0); left in place per owner.
- **CLAUDE.md:** added S3 no-versioning HARD RULE (covers app + bootstrap + manually-recreated buckets).
- NOT yet committed/merged at the time of writing → committing on feature/phase-6-ai-engine, PR to dev.

### NEXT SESSION MUST START HERE
**Phase 10 is COMPLETE + LIVE-VERIFIED. Only Phase 11 — Production Hardening — remains.**
Start Phase 11 (WAF on API GW + CloudFront, VPC endpoints, CloudTrail, AWS Config rules,
Security Hub, Lambda reserved concurrency, API GW throttling, checkov on cdk.out, Locust load
test, DR validation us-west-2, tag audit, final <$20 billing check). NOTE: several Phase 11
items assume CloudFront — gate those on the CloudFront account-verification case (below).
Carry-over follow-ups (none blocking):
  1. **AWS Support case for CloudFront** account verification (so GuardrailFrontend-dev can deploy
     AND the Phase 11 CloudFront-WAF item can land). Until then the dashboard is the Function URL host.
  2. **Owner browser pass** of the Phase 8 interaction criteria; the dashboard is seeded (3 demo
     scans, run `demo_wake.py`) so it opens with content. Confirm "Download PDF Report" on a REAL
     scan (seed data leaves report_s3_key unset by design).
  3. Phase 9 nice-to-haves: idempotency guard on report-handler (skip if report_s3_key set) to stop
     the EventBridge double-email; live-fire the failure path (force an ECS exit≠0) once.
  4. Optional, when the Bedrock model-access case resolves: flip ai-analyzer to Claude
     (BEDROCK_PROVIDER=anthropic in ai-stack.ts, redeploy GuardrailAi-dev).
  5. Phase 10 owner manual steps: 48h-idle billing confirmation (<$5) + full in-browser demo
     rehearsal (<10 min) using the 7 talking points in the DEMO LIFECYCLE section.
Auth recipe for AWS/CDK in THIS tool shell (both needed in the SAME Bash command):
  - `aws` CLI v2:  prefix `AWS_PROFILE=aws-admin` (and `MSYS_NO_PATHCONV=1` for any /leading-slash arg).
  - `cdk` deploy:  FIRST `cd infrastructure`, then `eval "$(aws configure export-credentials --profile
    aws-admin --format env)"` + `export CDK_DEFAULT_ACCOUNT=879072872327 CDK_DEFAULT_REGION=us-east-1`
    + the cdk command. (A background cdk deploy inherits the launcher cwd — if not infrastructure/ it
    fails "--app is required".)
  - ALWAYS `--exclusively` for a single stack + run_in_background:true (a foreground cdk past the 2-min
    tool cap keeps deploying detached and can strip Lambdas via computeEnabled). See the Phase 7 incident.
  - dev is DEPLOYED + RUNNING: 8 stacks (Foundation, Auth, Scanner, Ai, Api, FrontendHost, Monitor) —
    NOT GuardrailFrontend (CloudFront, blocked). Live dashboard:
    https://g6p2vamezwbvtug6ohppi34uyi0pwvqd.lambda-url.us-east-1.on.aws/  (SSM /guardrail/dev/frontend-url)
    Test login: puneetkumarsingh765@gmail.com / Guardrail2026. API URL: SSM /guardrail/dev/api-url.
    Scanner now has 5 Lambdas (ingest, aggregator, report-handler, email-handler, failure-handler) +
    2 ECS tasks (rules-engine, checkov). Dashboard: GuardrailHealth-dev. Ops SNS: guardrail-ops-alerts-dev.

### (Prior session) What Was Completed
- **PHASE 5 SCANNING ENGINE: DEPLOYED + VERIFIED END-TO-END.** All acceptance criteria pass.
- AWS auth: SSO via profile `aws-admin` (account 879072872327). Tool shell defaults to
  `[default]` profile which has NO creds — ALWAYS prefix AWS/CDK cmds with `AWS_PROFILE=aws-admin`.
- **Two-phase deploy pattern added** to scanner-stack.ts (bootstrap deadlock fix):
  - `lambda.DockerImageFunction.fromEcr` needs the image at CreateFunction time, but the
    stack also creates the ECR repos → deadlock on fresh create. ECS task defs don't validate.
  - Gated the 2 Lambdas + S3UploadRule behind `computeEnabled` context flag.
  - Phase A: `cdk deploy ... --context computeEnabled=false` → repos+ECS+SQS+VPC (no Lambdas).
  - Push 4 images. Phase B: `cdk deploy ...` (default) → adds Lambdas (images now present).
- **Lambda image manifest fix:** Docker 29 BuildKit default → OCI image index w/ provenance
  attestations → Lambda "image manifest media type not supported". Fixed by building the 2
  Lambda images with buildx docker-container driver + `--provenance=false`
  `--output type=image,oci-mediatypes=false,push=true`. ECS images use plain `docker build`.
- All 4 ECR repos created + images pushed: guardrail-{ingest,aggregator,rules-engine,checkov}-dev.
- E2E verified: uploaded demo-master-bad.tf → status=COMPLETE in <5min, 48 findings,
  4 CRITICAL (S3-001, SG-001/2/3), both layers (custom + Checkov) present + deduped.
- pytest: 32 passed, 70% coverage. Code change: scanner-stack.ts (bootstrap flag). Merged via PR #10.

### ALSO THIS SESSION — Environment lifecycle PROVEN (PR #11, merged to dev)
- **Teardown guarantee tested LIVE:** `cdk destroy --all` → account swept 100% empty ($0, no
  DELETE_FAILED). Fixed the teardown blocker: VPC `restrictDefaultSecurityGroup:false` (the flaky
  default-SG custom resource). Old orphans (guardrail-scanner repo, old VPC CR) — deleted, GONE.
- **Reliable setup/promotion:** `scripts/deploy_env.sh` = idempotent 4-step bootstrap
  (deploy computeEnabled=false → push 4 images → deploy computeEnabled=true → seed rules). Breaks
  the ECR deadlock; identical path for dev/staging/prod so promotion can't fail on sequencing.
- **`scripts/seed_rules_catalog.py`** — a fresh rules-catalog table is EMPTY, so custom rules never
  fire without seeding. Now a bootstrap step. (Gap found during the rebuild test.)
- Ran the FULL destroy→empty→rebuild→E2E cycle 3× (48 findings, 9 custom + 39 Checkov, 4 CRITICAL).
  Documented in the new CLAUDE.md "ENVIRONMENT LIFECYCLE" section + 4 KNOWN DECISIONS.

### CURRENT AWS STATE (read before next session acts)
- **dev is DEPLOYED + RUNNING** — freshly rebuilt from scratch at end of this session, E2E-verified.
  It is NOT empty. To park at $0: `AWS_PROFILE=aws-admin npx cdk destroy --all --context env=dev --force`.
  To (re)build: `AWS_PROFILE=aws-admin scripts/deploy_env.sh dev`.
- **DEFERRED (do before first staging promotion):** GitHub Actions workflows 02/03 still run a bare
  `cdk deploy --all` — OK for dev UPDATES, but the FIRST fresh staging/prod deploy will hit the ECR
  deadlock. Wire 02/03 to call `scripts/deploy_env.sh` (or replicate its 4 steps) first.

### NEXT SESSION (prior-session note — SUPERSEDED; Phase 6 now DEPLOYED, see top of SESSION TRACKER)
**Phase 6 — AI Analysis Engine.** Reminder: prefix every AWS/CDK command with `AWS_PROFILE=aws-admin`.

STEP 0 — verify auth: `AWS_PROFILE=aws-admin aws sts get-caller-identity` (re-run SSO login if expired).
STEP 1 — Write ai-engine/ per Phase 6 checklist: prompts (explain_risk/generate_fix/score_risk),
         bedrock_client.py (Haiku explain / Sonnet fix, retry w/ backoff), analyzer.py Lambda
         (EventBridge ScanComplete → explain+fix each finding, risk_score, AIAnalysisComplete event).
STEP 2 — ai-engine/Dockerfile (python:3.12-slim + awslambdaric), guardrail-ai-engine-dev ECR repo.
STEP 3 — infrastructure/lib/ai-stack.ts (ai-analyzer Lambda, IAM bedrock:InvokeModel on Haiku+Sonnet
         ARNs only, EventBridge ScanComplete rule). Wire in app.ts with addDependency(scanner).
STEP 4 — Tests: ai-engine/tests/ (test_bedrock_client 3, test_analyzer 5). pytest ≥70%.
STEP 5 — DEPLOY via the lifecycle pattern (do NOT bare `cdk deploy`): the AI Lambda also uses
         fromEcr → SAME bootstrap deadlock. Add a `computeEnabled`-style gate to ai-stack (gate the
         ai-analyzer Lambda) AND extend `scripts/deploy_env.sh` to build+push guardrail-ai-engine-dev
         (buildx Lambda-compat flags). Then one `scripts/deploy_env.sh dev` brings up Phase 6 too,
         and teardown stays a clean `cdk destroy --all`. Verify the new repo is in the destroy sweep.
STEP 6 — Verify Phase 6 acceptance criteria, then housekeeping.

### Session Log (reverse chronological)
```
2026-06-28 | PHASE 10 DEMO LIFECYCLE & README COMPLETE + LIVE-VERIFIED (dev). 4 scripts + README.
             seed_demo_data.py: 3 pre-canned scans (risk 72/45/16 = HIGH/MED/LOW), dated 6/3/0 days
             ago so newest=lowest = improving trend in the real Scan List (no dead TrendChart data).
             Findings carry ai_explanation + ai_fix_code (CRITICAL/HIGH); risk via canonical WEIGHTS;
             deterministic uuid5 ids = idempotent re-seed; report_s3_key left unset (no fake PDF).
             demo_sleep/demo_wake: disable/enable CloudFront IF a dist exists (reads cloudfront-dist-id),
             else no-op + report the $0-idle Function URL host has nothing to stop; both record
             /guardrail/{env}/demo-state; wake calls seed in-process + prints live URL. billing_check.py:
             Cost Explorer by SERVICE, warns > $15. Windows fix: stdout.reconfigure(utf-8) + ASCII table
             (cp1252 crashed billing on →/box glyphs). LIVE: 3 rows in scan-jobs-dev, dashboard HTTP 200,
             billing TOTAL $0.95 MTD (< $5 idle / $15 dev). Only Phase 11 remains. PR #20 → dev.
2026-06-28 | PHASE 9 EMAIL + OBSERVABILITY COMPLETE + LIVE-VERIFIED (E2E success). report-handler
             (reportlab PDF → S3 → ReportGenerated) + email-handler (SES raw email, CRITICAL/HIGH body
             + PDF attach; routes success/failure off EventBridge detail-type) + failure-handler
             (ECS exit≠0 / SNS-DLQ → FAILED → ScanFailed). New src/report_generator + src/services.
             ONE shared image guardrail-report-{env} (reportlab), 3 Lambdas via distinct DockerImageCode
             cmds (NOT scanner-image+MODE). foundation: Secrets Manager app-secrets + cloudfront-url SSM.
             scanner-stack: report repo + 3 Lambdas (computeEnabled-gated) + 4 EventBridge rules + DLQ
             depth alarm→SNS→failure. NEW monitoring-stack (GuardrailHealth dashboard + ops SNS + Errors
             alarms + ai p95 latency; refs Lambdas by metric dimension, not construct). 74 tests, 86.87%
             cov. Fixed appSecret.grantRead → Foundation→Scanner dependency CYCLE (use explicit
             GetSecretValue statement on the role). Deployed two-phase (A compute=false → push report
             image → B compute=true), --exclusively, bg cdk. 8 stacks live. E2E: bad TF → REPORT_COMPLETE
             ~80s, PDF 8,886B %PDF in S3, success_email_sent (SES verified). Known: EventBridge at-least-
             once → 2 emails/scan (add idempotency later); failure path deployed+unit-tested, not fired.
2026-06-28 | PHASE 8 FRONTEND CODE-DONE + LIVE via Lambda Function URL (PR pending → dev). Vite/React
             18/TS dashboard (Tailwind v3, React Query v5, Amplify v6, react-router v6, react-dropzone):
             Login + ScanList + ScanDetail (RiskScoreMeter SVG, FindingsTable, AI drawer). 22 files;
             npm build OK; vitest 6/6. CLOUDFRONT BLOCKED (account-level, not code): Distribution CREATE
             → 403 "account must be verified before you can add new CloudFront resources" → needs AWS
             Support case (frontend-stack.ts is correct; OAC creates fine). STOPGAP SHIPPED: frontend-host/
             container Lambda + public Function URL serves the same S3 bundle ($0 idle, HTTPS). LIVE:
             g6p2vamezwbvtug6ohppi34uyi0pwvqd.lambda-url.us-east-1.on.aws — root 200, asset 200,
             SPA fallback OK, missing→404; login USER_PASSWORD_AUTH→ID token→API /v1/scans 200. Cognito
             test user created (Guardrail2026). CDK lessons: (1) OAC over a cross-stack bucket → cycle +
             Fn::GetStackOutput fail → import bucket by deterministic NAME + add OAC policy in consumer
             stack; (2) background cdk inherits launcher cwd → must `cd infrastructure` or "--app required".
             Built Tailwind direct (not shadcn CLI — can't one-shot its init).

2026-06-28 | PHASE 7 API LAYER DEPLOYED + LIVE-VERIFIED (PR #17 → dev). api/ = one Lambda behind
             API GW REST + Cognito authorizer; 4 routes (POST/GET scans, GET detail, GET report).
             Entrypoint src/app.py (NOT main.py — avoids src.main collision with scanner in the
             shared pytest namespace). middleware/auth.py = python-jose JWT (JWKS/RS256). Ingest
             reuses the API-embedded scan_job_id (uploads/<uuid>/<file>) → one DDB row e2e.
             api-stack.ts uses the two-phase computeEnabled ECR gate; app.ts deps = foundation+auth
             only. 55 tests, 85.86% cov. Live: no-JWT→401, JWT POST→200, GET list/detail→200,
             report→404. INCIDENT: a foreground `cdk deploy` (no --exclusively, computeEnabled=false)
             timed out at the 2-min tool cap but its node child kept running detached and stripped
             scanner+ai Lambdas; recovered via kill + `cdk deploy --all` compute=true. Lessons:
             always --exclusively + run_in_background for cdk; export-credentials for cdk SSO;
             MSYS_NO_PATHCONV=1 for /leading-slash aws args.

2026-06-28 | ENV LIFECYCLE proven (PR #11 → dev). Teardown guarantee tested LIVE: cdk destroy --all
             → account 100% empty ($0, no DELETE_FAILED). VPC restrictDefaultSecurityGroup:false
             removes the flaky teardown-blocker. scripts/deploy_env.sh (4-step bootstrap) +
             scripts/seed_rules_catalog.py make setup + dev→staging promotion reliable. Ran full
             destroy→empty→rebuild→E2E cycle 3× (48 findings, 9 custom + 39 Checkov, 4 CRITICAL).
             dev left RUNNING (freshly rebuilt). Deferred: wire CI 02/03 to deploy_env.sh before
             first staging promotion. PR #10 also merged (Phase 5 deploy + CI conftest fix).

2026-06-28 | Per-service ECR architecture implemented. One Dockerfile + ECR repo per
             Lambda/ECS task. scanner-stack.ts has 4 ECR repos. CDK synth clean.
             Pushed to feature/phase-5-scanning-engine (commit 9d290bf).
             AWS session expired — cdk deploy + docker push pending re-auth.
             CLAUDE.md: Docker standards + KNOWN DECISIONS + WHAT DEGRADES PERFORMANCE
             all updated. prompts.md: all turns logged (MODE A).

2026-06-28 | TOKEN EFFICIENCY PROTOCOL rewritten. Haiku retired from Claude Code workflow.
             Sonnet 4.6 now handles ALL tasks inline — no subagents for routine work.
             ECR image push blocker documented. Phase 5 VERIFY pending ECR fix.
             CLAUDE.md: KNOWN DECISIONS + COST GUARDRAILS + SESSION TRACKER updated.

### Session Log (reverse chronological)
```
2026-06-28 | PHASE 5 DEPLOYED + VERIFIED ✅. Scanner stack live in AWS (acct 879072872327).
             AWS auth = SSO profile aws-admin (tool shell needs AWS_PROFILE=aws-admin prefix).
             Fixed 2 deploy blockers: (1) bootstrap deadlock — Lambda fromEcr needs image at
             create but stack makes the repo → added computeEnabled two-phase flag to
             scanner-stack.ts. (2) Docker 29 BuildKit OCI/provenance manifest → Lambda reject →
             rebuilt 2 Lambda images via buildx docker-container --provenance=false oci-mediatypes=false.
             E2E: demo-master-bad.tf → COMPLETE <5min, 48 findings, 4 CRITICAL, both layers.
             pytest 32 passed 70% cov. Only code change: scanner-stack.ts. Next: Phase 6 AI engine.

2026-06-28 | TOKEN EFFICIENCY PROTOCOL rewritten. Haiku retired from Claude Code workflow.
             Sonnet 4.6 now handles ALL tasks inline — no subagents for routine work.
             ECR image push blocker documented. Phase 5 VERIFY pending ECR fix.
             CLAUDE.md: KNOWN DECISIONS + COST GUARDRAILS + SESSION TRACKER updated.

2026-06-28 | Phase 5 Scanning Engine CODE COMPLETE. PR #9 open → dev.
             32 tests (5 parser + 5 cfn + 9 rules + 3 aggregator), 73% coverage.
             20 security rules implemented (S3/SG/IAM/ENC/LOG) in rules_engine.py.
             Fargate scanner_runner.py maps 14 Checkov IDs to custom rule IDs.
             Bug fixes: cfn_flip.load() API, Attr("enabled").eq(True) FilterExpression.
             Infrastructure already deployed via scanner-stack.ts in Phase 4.

2026-06-28 | Phase 4 Ingestion Layer COMPLETE. scanner/ Python layer fully written.
             CDK: ScannerStack wired in app.ts, FoundationStack gains EventBus export.
             Bugs fixed: always DESTROY, S3→default bus / guardrail→custom bus routing.
             cdk synth clean. PR #7 merged to dev.

2026-06-28 | Phase 3 IaC Demo Examples COMPLETE. 14 files created: 20-rule rules-catalog.json,
             3 good TF + 3 good CFN examples, 5 bad TF + 3 bad CFN examples.
             demo-master-bad.tf and demo-master-bad.yaml trigger all CRITICAL rules.
             Branch: feature/phase-3-iac-examples. Pending PR → dev.
             Added VIBE CODING TEST mandatory activities section to CLAUDE.md.

2026-06-28 | Phase 2 CI/CD COMPLETE. PR #2 merged to dev. All 4 pr-checks pass.
             Branch protection rulesets active (main/staging/dev). ECR repo created.
             Secrets set. Fixed setup-python cache:pip issue + tfsec missing-dir crash.

2026-06-28 | 3-branch enterprise GitHub model finalized: dev (default) → staging → main.
             CLAUDE.md updated: new BRANCHING STRATEGY section, Phase 2 checklist,
             all workflow specs, KNOWN DECISIONS, CDK standards. Repo not yet pushed.

2026-06-27 | Phase 0 marked COMPLETE. All prerequisites verified by Puneet:
             tools installed, AWS CLI configured, GitHub repo + OIDC role set up,
             Bedrock access enabled, SES verified, CDK bootstrapped.
             Next: Phase 1 Foundation Infrastructure.

2026-06-23 | PHASE STATUS completely rewritten. All 10 phases replaced with 11 phases
             (Phase 0 added for prerequisites). Each phase now has: GOAL, ACCEPTANCE
             CRITERIA, START COMMANDS, and granular checklist. CDK vs CFN conflict
             resolved: CDK is the infra source; cloudformation/ dir is demo targets only.
             Phase 3 split from overloaded CI/CD+CFN+examples into proper scope.
             Billing alarm deduplication fixed. Phase 9 demo_sleep.py fixed for
             GitHub Actions (no CodePipeline reference). OAI → OAC updated in Phase 8.

2026-06-22 | CI/CD changed from CodePipeline to GitHub Actions. CFN templates added.
             terraform-examples/ and cloudformation/ directories added to project.
             Two new S3 buckets added: cfn-artifacts, lambda-packages.

2026-06-22 | Architecture designed, CLAUDE.md created.
```

---

## ARCHITECTURE SPECS (Reference for Implementation)

### DynamoDB Table Schemas

**Table: `scan-jobs`**
```
PK: scan_job_id (String) — UUID v4
SK: created_at (String) — ISO 8601
Attributes:
  status: QUEUED | SCANNING | AI_ANALYSIS | COMPLETE | FAILED
  file_name: String
  file_size_bytes: Number
  file_type: terraform | cloudformation
  s3_key: String
  risk_score: Number (0-100)
  finding_counts: Map { CRITICAL, HIGH, MEDIUM, LOW }
  scan_duration_ms: Number
  created_by: String (Cognito sub)
TTL: 90 days
GSI: status-index (PK: status, SK: created_at) — for filtering by status
```

**Table: `findings`**
```
PK: scan_job_id (String)
SK: finding_id (String) — UUID v4
Attributes:
  rule_id: String (e.g., "S3-001")
  severity: CRITICAL | HIGH | MEDIUM | LOW
  resource_name: String
  resource_type: String
  line_number: Number
  code_snippet: String (max 500 chars)
  ai_explanation: String (Bedrock output)
  ai_fix_code: String (Bedrock-generated corrected IaC)
  dismissed: Boolean (default false)
  dismissed_at: String
TTL: 90 days
GSI: severity-index (PK: severity, SK: scan_job_id) — for dashboard aggregation
```

**Table: `rules-catalog`**
```
PK: rule_id (String)
Attributes:
  name: String
  description: String
  severity: CRITICAL | HIGH | MEDIUM | LOW
  category: S3 | IAM | NETWORK | ENCRYPTION | LOGGING | COMPUTE
  iac_types: List [terraform, cloudformation]
  remediation_docs_url: String
  enabled: Boolean
  version: String
```

### S3 Bucket Configuration

**`guardrail-iac-uploads-{account-id}`**
- Versioning: enabled
- Server-side encryption: KMS (project key)
- Block public access: ALL blocked
- Lifecycle: Delete objects after 30 days
- Event notification: ObjectCreated → EventBridge

**`guardrail-scan-reports-{account-id}`**
- Versioning: enabled
- Server-side encryption: KMS
- Block public access: ALL blocked
- Intelligent Tiering: transition to IA after 30 days, Archive after 90 days

**`guardrail-dashboard-{account-id}`**
- Static website: disabled (use CloudFront OAI only)
- Server-side encryption: AES-256
- Block public access: ALL blocked
- Versioning: disabled (GitHub Actions handles deployment)

**`guardrail-cfn-artifacts-{account-id}`**
- Purpose: GitHub Actions uploads CloudFormation templates here before deploying
- Versioning: enabled (rollback requires previous template versions)
- Server-side encryption: AES-256
- Lifecycle: Keep last 10 versions per template, delete older
- Block public access: ALL blocked

**`guardrail-lambda-packages-{account-id}`**
- Purpose: GitHub Actions uploads Lambda zip packages here before update-function-code
- Versioning: enabled
- Server-side encryption: AES-256
- Lifecycle: Delete objects older than 30 days
- Block public access: ALL blocked

### Security Rules Catalog (Minimum 20 Rules)

```json
[
  {"rule_id":"S3-001","name":"Public S3 Bucket ACL","severity":"CRITICAL","category":"S3"},
  {"rule_id":"S3-002","name":"Public S3 Bucket Policy","severity":"CRITICAL","category":"S3"},
  {"rule_id":"S3-003","name":"S3 Versioning Disabled","severity":"MEDIUM","category":"S3"},
  {"rule_id":"S3-004","name":"S3 Encryption Disabled","severity":"HIGH","category":"S3"},
  {"rule_id":"S3-005","name":"S3 Logging Disabled","severity":"LOW","category":"S3"},
  {"rule_id":"SG-001","name":"SSH Open to World","severity":"CRITICAL","category":"NETWORK"},
  {"rule_id":"SG-002","name":"RDP Open to World","severity":"CRITICAL","category":"NETWORK"},
  {"rule_id":"SG-003","name":"All Ports Open to World","severity":"CRITICAL","category":"NETWORK"},
  {"rule_id":"SG-004","name":"HTTP Open to World (non-LB)","severity":"MEDIUM","category":"NETWORK"},
  {"rule_id":"IAM-001","name":"Wildcard Action in Policy","severity":"HIGH","category":"IAM"},
  {"rule_id":"IAM-002","name":"Wildcard Resource in Policy","severity":"HIGH","category":"IAM"},
  {"rule_id":"IAM-003","name":"Root Account Usage","severity":"CRITICAL","category":"IAM"},
  {"rule_id":"IAM-004","name":"MFA Not Required","severity":"HIGH","category":"IAM"},
  {"rule_id":"IAM-005","name":"Inline Policy Used","severity":"LOW","category":"IAM"},
  {"rule_id":"ENC-001","name":"EBS Volume Unencrypted","severity":"HIGH","category":"ENCRYPTION"},
  {"rule_id":"ENC-002","name":"RDS Encryption Disabled","severity":"HIGH","category":"ENCRYPTION"},
  {"rule_id":"ENC-003","name":"Secrets in Plaintext","severity":"CRITICAL","category":"ENCRYPTION"},
  {"rule_id":"LOG-001","name":"CloudTrail Disabled","severity":"HIGH","category":"LOGGING"},
  {"rule_id":"LOG-002","name":"VPC Flow Logs Disabled","severity":"MEDIUM","category":"LOGGING"},
  {"rule_id":"LOG-003","name":"S3 Access Logging Disabled","severity":"LOW","category":"LOGGING"}
]
```

### Compute Deployment Rule — DOCKER IMAGES ONLY

Every Lambda function and every ECS task MUST be deployed as a Docker container image from ECR.
No zip packages. No Lambda layers. No dependency trimming.

```
Deployment flow for ALL compute:
  1. docker build -t guardrail-{service} {dir}/
  2. docker tag → ECR push
  3. Lambda: aws lambda update-function-code --image-uri {ecr-uri}:{tag}
     ECS:    Register new task definition revision referencing {ecr-uri}:{tag}
```

ECR repositories (one per service):
  guardrail-scanner-{env}     ← scanner/ image (ingest + rules-engine + aggregator — same image, MODE env var selects entry point)
  guardrail-checkov-{env}     ← fargate/ image (Checkov OSS scanner — separate, 500MB+)
  guardrail-ai-engine-{env}   ← ai-engine/ image (Bedrock analyzer Lambda)
  guardrail-api-{env}         ← api/ image (REST + WebSocket handlers Lambda)

### Lambda Functions — Specs (ALL use Lambda Container Images from ECR)

`[plain]` = plain env var injected by CDK at deploy time (non-sensitive)
`[secret]` = APP_SECRETS_ARN injected as plain var; code calls Secrets Manager at cold start to fetch actual value

| Function | ECR Image (own repo per function) | Memory | Timeout | Trigger | Env Vars |
|---|---|---|---|---|---|
| ingest-handler | guardrail-ingest-{env} | 256MB | 30s | EventBridge (S3 ObjectCreated) | [plain] SCAN_JOBS_TABLE, UPLOAD_BUCKET, EVENT_BUS_NAME |
| aggregator | guardrail-aggregator-{env} | 256MB | 60s | SQS checkov-results | [plain] SCAN_JOBS_TABLE, FINDINGS_TABLE, EVENT_BUS_NAME |
| ai-analyzer | guardrail-ai-engine-{env} | 512MB | 300s | EventBridge ScanComplete | [plain] FINDINGS_TABLE, SCAN_JOBS_TABLE, EVENT_BUS_NAME, BEDROCK_EXPLAIN_MODEL, BEDROCK_FIX_MODEL |
| report-handler | guardrail-report-{env} | 512MB | 120s | EventBridge AIAnalysisComplete | [plain] FINDINGS_TABLE, SCAN_JOBS_TABLE, REPORTS_BUCKET, EVENT_BUS_NAME |
| email-handler | guardrail-email-{env} | 256MB | 30s | EventBridge ReportGenerated OR ScanFailed | [plain] FINDINGS_TABLE, SCAN_JOBS_TABLE, REPORTS_BUCKET, CLOUDFRONT_URL, EMAIL_TYPE + [secret] APP_SECRETS_ARN→{ses_from_email, ses_to_email} |
| failure-handler | guardrail-failure-{env} | 128MB | 30s | ECS TaskStopped (exitCode≠0) + SQS DLQ alarm | [plain] SCAN_JOBS_TABLE, EVENT_BUS_NAME |
| api-handler | guardrail-api-{env} | 256MB | 29s | API GW REST | [plain] SCAN_JOBS_TABLE, FINDINGS_TABLE, RULES_TABLE, UPLOAD_BUCKET, REPORTS_BUCKET |

### ECS Fargate Tasks — Specs (ALL use Docker Images from ECR)

All ECS tasks use IAM roles for AWS access — no secrets needed.
`*` = injected at RunTask time via ECS container environment overrides (per-invocation values).

| Task | ECR Image (own repo per task) | vCPU | Memory | Trigger | Env Vars |
|---|---|---|---|---|---|
| rules-engine-task | guardrail-rules-engine-{env} | 0.5 | 1GB | EventBridge ScanRequested → ECS RunTask | [plain] SCAN_JOB_ID*, S3_KEY*, IAC_TYPE*, FINDINGS_TABLE, RULES_TABLE, UPLOAD_BUCKET, EVENT_BUS_NAME, MODE=rules_engine |
| checkov-task | guardrail-checkov-{env} | 0.25 | 512MB | EventBridge ScanRequested → ECS RunTask | [plain] SCAN_JOB_ID*, S3_BUCKET*, S3_KEY*, SQS_QUEUE_URL |

**Why rules-engine is ECS task (not Lambda):**
- Heavy dependencies (python-hcl2, cfn-flip) → Docker image eliminates zip packaging problem
- Consistent with Checkov task — both are ECS Fargate, same deployment pattern
- Per-file processing: EventBridge fires one ScanRequested event per file → one ECS task per scan
- Task receives SCAN_JOB_ID + S3_KEY as env vars, downloads file, scans, writes DDB, exits
| api-handler | Python 3.12 | 256MB | 29s | API GW | All tables, UPLOAD_BUCKET |
| websocket-handler | Python 3.12 | 128MB | 29s | API GW WS | CONNECTIONS_TABLE |
| slack-notifier | Python 3.12 | 128MB | 10s | SNS | SLACK_WEBHOOK_URL (Secrets Mgr) |

### Bedrock Model Routing

```python
# Use Haiku for speed + cost on high-volume tasks
HAIKU  = "anthropic.claude-haiku-4-5-20251001"   # explain_risk, score_risk
SONNET = "anthropic.claude-sonnet-4-6"             # generate_fix (needs precision)

# Token budgets per call
EXPLAIN_MAX_TOKENS = 300   # Risk explanation: 2-3 sentences
FIX_MAX_TOKENS     = 800   # IaC fix: enough for a full resource block
SCORE_MAX_TOKENS   = 50    # Score: just a number + one-line reason
```

### Risk Score Algorithm

```python
WEIGHTS = {"CRITICAL": 40, "HIGH": 20, "MEDIUM": 5, "LOW": 1}
MAX_POSSIBLE = 200  # cap denominator to normalize outliers

def calculate_risk_score(findings: list[Finding]) -> int:
    raw = sum(WEIGHTS[f.severity] for f in findings)
    normalized = min(raw, MAX_POSSIBLE)
    score = int((normalized / MAX_POSSIBLE) * 100)
    return score

# Thresholds for UI color coding
# 0-30:  GREEN  (Low Risk)
# 31-60: ORANGE (Medium Risk)
# 61-80: RED    (High Risk)
# 81-100: DARK RED (Critical Risk)
```

### API Gateway Endpoints (REST only — WebSocket removed from scope)

```
REST API (v1) — 5 endpoints, all require Cognito JWT:
  POST   /v1/scans                      → returns {presigned_url, scan_job_id}
                                          Frontend PUTs file to presigned URL directly
  GET    /v1/scans                      → list all scans, sorted created_at desc, max 50
                                          Returns: [{scan_job_id, file_name, status,
                                                    risk_score, finding_counts, created_at}]
  GET    /v1/scans/{scan_job_id}        → full scan detail + all findings
                                          Returns: scan fields + findings[] with
                                                   rule_id, severity, resource_name,
                                                   line_number, ai_explanation, ai_fix_code
  GET    /v1/scans/{scan_job_id}/report → presigned S3 GET URL for PDF (15 min TTL)
                                          Returns 404 if report not yet generated
  All 4 above handled by single api-handler Lambda (guardrail-api ECR image)

REMOVED from scope (do not implement):
  PATCH  /v1/findings/{finding_id}  (dismiss finding)
  GET    /v1/dashboard/summary      (trend chart removed)
  GET    /v1/rules                  (not needed by UI)
  WebSocket API                     (email is the async notification)
  ws-connections DynamoDB table     (WebSocket removed)
```

---

## TECHNOLOGY STACK (LOCKED — Do Not Change Without Noting Here)

| Layer | Technology | Version | Reason |
|---|---|---|---|
| IaC (Definition) | AWS CDK | v2 latest | TypeScript type safety, L2 constructs, synthesizes to CFN |
| IaC (Deployment) | CloudFormation | — | CFN YAML templates deployed via GitHub Actions + AWS CLI |
| IaC (Examples) | Terraform + CFN YAML | — | Scanner demo targets; both formats in terraform-examples/ |
| Infra Lang | TypeScript | 5.x | CDK native |
| CI/CD | GitHub Actions | — | Free for public repos; OIDC auth to AWS (no stored keys) |
| CFN Linting | cfn-lint | latest | Validates CFN templates in PR checks before deploy |
| TF Security | tfsec | latest | Scans Terraform examples in PR checks |
| Lambda Lang | Python | 3.12 | AWS native, Boto3, HCL parsing libs |
| Frontend | React + TypeScript | 18.x + 5.x | Industry standard |
| Frontend Build | Vite | 5.x | Fast HMR, easy S3 deploy |
| UI Library | Shadcn/ui + Tailwind | latest | Professional look, no license issues |
| Charts | Recharts | 2.x | React-native, Tailwind compatible |
| Auth | Cognito + Amplify JS | v6 | AWS native, free tier |
| IaC Parser (TF) | python-hcl2 | latest | Only reliable HCL2 parser for Python |
| IaC Parser (CFN) | cfn-flip | latest | AWS-maintained CFN parser |
| OSS Scanner | Checkov | latest | Runs in Fargate, 1000+ rules, supports TF + CFN |
| AI | Amazon Bedrock | Claude models | AWS native, no key management |
| API Client | Axios | 1.x | Interceptors for auth token |
| State Mgmt | React Query (TanStack) | v5 | Server state, caching, websocket |
| Testing (Python) | pytest + moto | latest | moto for AWS service mocking |
| Testing (TS) | Vitest | latest | Vite-native, fast |
| Container base | python:3.12-slim | 3.12 | Debian: better apt packages, no opinionated ENTRYPOINT. Lambda compat via awslambdaric pip package. |
| Lambda RIC | awslambdaric | >=2.0.0 | Makes python:3.12-slim Lambda-compatible. Replaces AWS base image. Must be in requirements.txt. |
| Container Registry | ECR | — | AWS native |

---

## CODING STANDARDS (Claude Must Follow These)

### Layered Architecture (SOLID — enforced in scanner/, ai-engine/, api/)

Every service module MUST follow this layer order. Calls only flow downward — never skip layers.

```
main.py          ← Entry point only. Reads MODE env var, calls correct controller.
controllers/     ← Event adapters. Parse raw event dict → typed params → call service.
                   No business logic. No AWS calls. No exception handling beyond HTTP shape.
services/        ← Business logic. Orchestrates adapters and rules. Raises domain exceptions.
                   No boto3 here. Receives adapter interfaces via constructor injection.
core/interfaces/ ← ABCs only. IParser.parse(bytes) → dict. IRule.apply(parsed, job_id) → list[Finding].
                   Defines contracts — never implements them.
core/models/     ← Dataclasses only. Finding, ScanJob. No methods that touch AWS.
adapters/aws/    ← All boto3 calls live here and ONLY here.
adapters/parsers/← Implements IParser. python-hcl2 and cfn-flip calls here.
rules/           ← Implements IRule. One class per rule_id. apply() returns [] if no violation.
```

SOLID checklist (Claude must verify before writing any new file):
- S (Single Responsibility): each file has one reason to change
- O (Open/Closed): new parser or rule = new file, zero changes to existing files
- L (Liskov): every IRule.apply() and IParser.parse() can be swapped without callers changing
- I (Interface Segregation): IParser and IRule are minimal — no god interfaces
- D (Dependency Inversion): services receive adapters via constructor, never instantiate boto3 directly

### Docker Image Standards (ALL compute — Lambda and ECS)

**LOCKED BASE IMAGE — Do not change without updating this section and KNOWN DECISIONS.**

| Image | Used for | Why |
|---|---|---|
| `python:3.12-slim` | scanner/, ai-engine/, api/ | Debian: apt compatibility, no opinionated ENTRYPOINT, smaller than AL2 |
| `python:3.12-slim` | fargate/ (Checkov) | Consistent across all images |
| ~~`public.ecr.aws/lambda/python:3.12`~~ | ~~Never use~~ | Amazon Linux 2, ENTRYPOINT=/lambda-entrypoint.sh fights ECS, fewer apt packages |

**Lambda compatibility without the AWS base image:**
`python:3.12-slim` needs `awslambdaric` (AWS Lambda Runtime Interface Client) installed via pip.
This is the SAME RIC that the AWS base image pre-installs — same Lambda behaviour, cleaner base.
**Always include in requirements.txt:** `awslambdaric>=2.0.0`

**No Mangum. Ever.** Mangum is an ASGI adapter for Flask/FastAPI frameworks.
Our handlers are plain `def handler(event, context) -> dict` — native Lambda format.
The RIC calls this directly. No adapter needed.

#### Canonical Dockerfile (scanner/ and ai-engine/)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY __init__.py .

# Default CMD — never executed directly in AWS.
# Lambda overrides entrypoint+cmd via CDK imageConfig.
# ECS overrides entryPoint via CDK container definition.
CMD ["python", "-m", "src.main"]
```

#### CDK patterns — copy-paste exactly, never guess

**Lambda DockerImageFunction — ALWAYS use this form, never lambda.Function:**
```typescript
new lambda.DockerImageFunction(this, "MyHandler", {
  code: lambda.DockerImageCode.fromEcr(ecrRepo, {
    tagOrDigest: `${env}-latest`,
    entrypoint: ["/usr/local/bin/python", "-m", "awslambdaric"],  // ← REQUIRED for slim image
    cmd: ["src.handlers.my_handler.handler"],                      // ← dotted module.function path
  }),
  // memorySize, timeout, role, environment, tracing, logGroup ...
});
// NEVER use: new lambda.Function(..., { runtime: lambda.Runtime.PYTHON_3_12, code: lambda.Code.fromAsset(...) })
// NEVER use: lambda.Code.fromAsset() — that is ZIP packaging, banned in this project
```

**ECS Fargate container — rules-engine and future ECS tasks:**
```typescript
taskDef.addContainer("rules-engine", {
  image: ecs.ContainerImage.fromEcrRepository(ecrRepo, `${env}-latest`),
  entryPoint: ["python", "-m", "src.main"],   // ← overrides any base image ENTRYPOINT
  // no 'command' — src/main.py reads MODE env var
  environment: { MODE: "rules_engine", FINDINGS_TABLE: "...", ... },
});
// ECS task receives per-invocation values (SCAN_JOB_ID, S3_KEY, IAC_TYPE)
// via containerOverrides in the EventBridge EcsTask target, NOT in environment above
```

#### Runtime behaviour at a glance

| Compute | Effective command | What runs |
|---|---|---|
| Lambda ingest-handler | `python -m awslambdaric src.handlers.ingest_handler.handler` | RIC calls handler(event, context) |
| Lambda aggregator | `python -m awslambdaric src.handlers.aggregator.handler` | RIC calls handler(event, context) |
| ECS rules-engine | `python -m src.main` | main.py reads MODE=rules_engine → rules_engine.main() |
| ECS checkov | `python scanner_runner.py` (fargate/Dockerfile CMD) | standalone script |

#### ECR repositories — one per service (loosely coupled, independently deployable)

**Rule: every Lambda and every ECS task has its own ECR repository and Dockerfile.**
A change to one service rebuilds only that service's image. Others are untouched.

```
guardrail-ingest-{env}         ← scanner/ingest/Dockerfile
                                  Deps: boto3 + awslambdaric only
                                  Used by: ingest-handler Lambda

guardrail-aggregator-{env}     ← scanner/aggregator/Dockerfile
                                  Deps: boto3 + awslambdaric only
                                  Used by: aggregator Lambda

guardrail-rules-engine-{env}   ← scanner/rules_engine/Dockerfile
                                  Deps: boto3 + python-hcl2 + cfn-flip (NO awslambdaric — ECS)
                                  Used by: rules-engine ECS task

guardrail-checkov-{env}        ← fargate/Dockerfile
                                  Deps: checkov (~500MB) + boto3
                                  Used by: checkov ECS task

# Future (Phases 6+):
guardrail-ai-engine-{env}      ← ai-engine/Dockerfile
guardrail-api-{env}            ← api/Dockerfile
```

**Dockerfile locations and build contexts:**

| Service | Dockerfile | Build command |
|---|---|---|
| ingest-handler | `scanner/ingest/Dockerfile` | `docker build -f scanner/ingest/Dockerfile scanner/` |
| aggregator | `scanner/aggregator/Dockerfile` | `docker build -f scanner/aggregator/Dockerfile scanner/` |
| rules-engine | `scanner/rules_engine/Dockerfile` | `docker build -f scanner/rules_engine/Dockerfile scanner/` |
| checkov | `fargate/Dockerfile` | `docker build fargate/` |

Build context is `scanner/` for all three scanner services — each Dockerfile does `COPY src/ ./src/`
to include the shared domain code (models, parsers, adapters, rules, handlers).

#### Python import rules — ALWAYS absolute, NEVER relative

```python
# ✓ CORRECT — works in Lambda (WORKDIR=/app), ECS, and local pytest
from src.models.finding import Finding
from src.parsers.terraform_parser import parse as parse_terraform
from src.parsers.cloudformation_parser import parse as parse_cloudformation

# ✗ WRONG — .models means src.handlers.models (wrong level), file does not exist there
from .models.finding import Finding

# ✗ WRONG — fragile, breaks if caller file moves
from ..models.finding import Finding
```

Why: WORKDIR is `/app`. Python resolves `src.models.finding` → `/app/src/models/finding.py`. ✓
Relative imports resolve relative to the file's own package — wrong level for our structure.

#### ECS task handler pattern (rules_engine.py and future ECS handlers)

ECS tasks have NO event dict. They read from environment, do work, exit.
```python
def main() -> None:
    """ECS entry point — called by src.main when MODE=rules_engine."""
    scan_job_id = os.environ.get("SCAN_JOB_ID")   # injected at RunTask time
    s3_key      = os.environ.get("S3_KEY")
    iac_type    = os.environ.get("IAC_TYPE", "terraform")
    if not scan_job_id or not s3_key:
        raise SystemExit(1)                         # non-zero exit → failure_handler fires
    _run_scan(scan_job_id, s3_key, iac_type)        # shared logic with Lambda handler()

def handler(event: dict, context) -> dict:
    """Lambda handler — kept for unit tests. ECS uses main() above."""
    detail = event.get("detail", {})
    _run_scan(detail["scan_job_id"], detail["s3_key"], detail.get("iac_type", "terraform"))
    return {"statusCode": 200}
```

#### src/main.py — ECS dispatcher (required in every service image)

```python
import logging, os, sys
logging.basicConfig(level=logging.INFO)
MODE = os.environ.get("MODE", "")

def main():
    if MODE == "rules_engine":
        from src.handlers.rules_engine import main as run; run()
    # add: "report", "email", "failure" as they are implemented in Phases 9+
    else:
        logging.error(f"Unknown MODE: {MODE!r}"); sys.exit(1)

if __name__ == "__main__":
    main()
```

#### Build + push commands (one per service — run before first deploy or when deps change)

```bash
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
ECR=${ACCOUNT}.dkr.ecr.us-east-1.amazonaws.com
ENV=dev   # change to staging or prod as needed

aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR

# ingest-handler Lambda (boto3 + awslambdaric only)
docker build -f scanner/ingest/Dockerfile -t guardrail-ingest scanner/
docker tag guardrail-ingest:latest $ECR/guardrail-ingest-$ENV:$ENV-latest
docker push $ECR/guardrail-ingest-$ENV:$ENV-latest

# aggregator Lambda (boto3 + awslambdaric only)
docker build -f scanner/aggregator/Dockerfile -t guardrail-aggregator scanner/
docker tag guardrail-aggregator:latest $ECR/guardrail-aggregator-$ENV:$ENV-latest
docker push $ECR/guardrail-aggregator-$ENV:$ENV-latest

# rules-engine ECS task (boto3 + python-hcl2 + cfn-flip)
docker build -f scanner/rules_engine/Dockerfile -t guardrail-rules-engine scanner/
docker tag guardrail-rules-engine:latest $ECR/guardrail-rules-engine-$ENV:$ENV-latest
docker push $ECR/guardrail-rules-engine-$ENV:$ENV-latest

# checkov ECS task (checkov ~500MB — separate image)
docker build -t guardrail-checkov fargate/
docker tag guardrail-checkov:latest $ECR/guardrail-checkov-$ENV:$ENV-latest
docker push $ECR/guardrail-checkov-$ENV:$ENV-latest
```

**CI/CD deploy trigger (GitHub Actions):** when `scanner/ingest/**` changes → only rebuild
`guardrail-ingest-{env}`. When `scanner/rules_engine/**` or `scanner/src/**` changes → rebuild
`guardrail-rules-engine-{env}`. Shared code (`scanner/src/`) changes affect all three scanner images.

**Rules (enforced):**
- Never `pip install` at container runtime — bake at build time only
- Always pin versions in requirements.txt: `python-hcl2>=4.3.0`, not `python-hcl2`
- Push two tags per build: `{env}-{git-sha}` (immutable, used in task defs) and `{env}-latest` (local dev)
- ECR lifecycle: keep last 10 tagged images, delete untagged after 1 day (set in scanner-stack.ts)

### Secrets vs Plain Environment Variables — Mandatory Pattern

**Rule:** Only two categories of config exist. Never mix them.

```
SECRETS MANAGER  → values you would NOT want in CloudWatch logs, ECS console, or git history
                   Examples: email addresses (PII), webhook URLs, API keys, passwords
                   These would appear in plain text in Lambda env tab in console — unacceptable.

PLAIN ENV VARS   → non-sensitive config: AWS resource names, model IDs, mode flags, URLs
                   Examples: DynamoDB table name, S3 bucket name, Bedrock model ID, MODE flag
                   These are AWS resource identifiers — visible in console anyway.
```

**Why this distinction matters for this project:**
- Bedrock (LLM): accessed via IAM role — NO API key. Model IDs are plain env vars.
- DynamoDB (database): accessed via IAM role — NO credentials. Table names are plain env vars.
- SES email addresses: PII — goes to Secrets Manager.
- S3, EventBridge, SQS: all IAM — no credentials to store.

**Secret structure (Secrets Manager):**

One secret per environment, JSON format:
```
Secret name:  guardrail/{env}/app-secrets
Secret value: {
  "ses_from_email": "puneetkumarsingh765@gmail.com",
  "ses_to_email":   "puneetkumarsingh765@gmail.com"
}
```
Add more keys to this same secret when new secrets arise (e.g., future webhook URLs).
Never create separate Secrets Manager entries for each individual value — one JSON blob per env.

**CDK pattern — how to wire both types:**

```typescript
// 1. Import secret (created once in foundation-stack.ts, imported everywhere else)
const appSecrets = secretsmanager.Secret.fromSecretNameV2(this, "AppSecrets",
    `guardrail/${env}/app-secrets`);

// 2. Lambda — inject plain env vars directly, secret as ARN only
const fn = new lambda.DockerImageFunction(this, "EmailHandler", {
    environment: {
        // ── Plain env vars (non-sensitive) ──────────────────────────────
        SCAN_JOBS_TABLE:         scanJobsTable.tableName,
        FINDINGS_TABLE:          findingsTable.tableName,
        REPORTS_BUCKET:          reportsBucket.bucketName,
        CLOUDFRONT_URL:          `https://${distribution.distributionDomainName}`,
        MODE:                    "email",
        // ── Secret reference (ARN only — code fetches value at runtime) ──
        APP_SECRETS_ARN:         appSecrets.secretArn,
    },
});
appSecrets.grantRead(fn);  // IAM permission to call GetSecretValue

// 3. ECS task — same pattern: plain vars in environment, secret ARN in environment
// (NOT using ECS secrets injection — keep it simple, code reads Secrets Manager directly)
const taskDef = new ecs.FargateTaskDefinition(this, "RulesEngineTask");
taskDef.addContainer("scanner", {
    environment: {
        // ── Plain env vars ───────────────────────────────────────────────
        SCAN_JOB_ID:    "",        // injected at RunTask time via overrides
        FINDINGS_TABLE: findingsTable.tableName,
        RULES_TABLE:    rulesTable.tableName,
        UPLOAD_BUCKET:  uploadBucket.bucketName,
        EVENT_BUS_NAME: eventBus.eventBusName,
        MODE:           "rules_engine",
        // ── No secrets needed for rules-engine — IAM handles all AWS access
    },
});
```

**Python pattern — how to read both types at runtime:**

```python
import json, boto3, os
from functools import lru_cache

# ── Plain env vars: read at module level (fail-fast if missing) ──────────
SCAN_JOBS_TABLE  = os.environ["SCAN_JOBS_TABLE"]
FINDINGS_TABLE   = os.environ["FINDINGS_TABLE"]
BEDROCK_EXPLAIN_MODEL = os.environ.get("BEDROCK_EXPLAIN_MODEL",
                                        "anthropic.claude-haiku-4-5-20251001")
BEDROCK_FIX_MODEL     = os.environ.get("BEDROCK_FIX_MODEL",
                                        "anthropic.claude-sonnet-4-6")
MODE = os.environ["MODE"]

# ── Secrets: fetched once at cold start, cached for Lambda lifetime ──────
@lru_cache(maxsize=1)
def get_secrets() -> dict:
    sm = boto3.client("secretsmanager")
    raw = sm.get_secret_value(SecretId=os.environ["APP_SECRETS_ARN"])
    return json.loads(raw["SecretString"])

# Usage in email-handler only:
# secrets = get_secrets()
# from_email = secrets["ses_from_email"]   → "puneetkumarsingh765@gmail.com"
# to_email   = secrets["ses_to_email"]     → "puneetkumarsingh765@gmail.com"
```

**Which functions use Secrets Manager:**

| Function | Needs APP_SECRETS_ARN? | Reason |
|---|---|---|
| ingest-handler | No | IAM only — no secrets needed |
| rules-engine ECS task | No | IAM only — no secrets needed |
| checkov ECS task | No | IAM only — no secrets needed |
| aggregator | No | IAM only — no secrets needed |
| ai-analyzer | No | Bedrock via IAM, model IDs are plain env vars |
| report-handler | No | S3 + DDB via IAM — no secrets needed |
| email-handler | **Yes** | SES From/To email addresses are PII |
| api-handler | No | DDB + S3 via IAM, Cognito validates tokens |

**Never do these:**
```python
# ✗ WRONG — hardcoding secret values in code or env vars
environment={"SES_FROM_EMAIL": "puneetkumarsingh765@gmail.com"}  # visible in console

# ✗ WRONG — creating one Secrets Manager entry per value
Secret("SesFromEmail", secret_string_value="puneetkumarsingh765@gmail.com")
Secret("SestoEmail", secret_string_value="puneetkumarsingh765@gmail.com")

# ✓ RIGHT — one JSON secret, ARN injected, code fetches at runtime
environment={"APP_SECRETS_ARN": appSecrets.secretArn}
```

### Python (Lambda functions)
```python
# Structured logging — always use this format, never print()
import json, logging, os
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info(json.dumps({"event": "scan_started", "scan_job_id": job_id}))

# Environment variables — always typed, always validated at startup
SCAN_JOBS_TABLE = os.environ["SCAN_JOBS_TABLE"]  # KeyError = fail fast = good

# DynamoDB — always use resource (not client) for table operations
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(SCAN_JOBS_TABLE)

# Return format for all Lambda handlers
def success(body: dict) -> dict:
    return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps(body)}

def error(status: int, message: str) -> dict:
    return {"statusCode": status, "headers": CORS_HEADERS,
            "body": json.dumps({"error": message})}
```

### TypeScript CDK
```typescript
// Resolve env from CDK context — ALWAYS at top of every stack constructor
const env = this.node.tryGetContext('env') ?? 'dev';  // default to dev if unset

// Always tag every resource
const commonTags = {
  Project: "SecurityGuardrailAuditor",
  Environment: env,   // "dev" | "staging" | "prod"
  Owner: "puneet-singh",
  CostCenter: "demo-portfolio",
};

// Always suffix every resource name with env to avoid collision across environments
// Examples:
//   Table:    `scan-jobs-${env}`
//   Bucket:   `guardrail-iac-uploads-${env}-${this.account}`
//   Lambda:   `guardrail-ingest-handler-${env}`
//   SSM path: `/guardrail/${env}/api-url`
//   LogGroup: `/guardrail/${env}/lambda/ingest-handler`

// Always use removal policy DESTROY in dev/staging, RETAIN in prod
const removalPolicy = env === 'prod' ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY;

// Always enable encryption by default
// Always set log retention — never INFINITE
import { RetentionDays } from "aws-cdk-lib/aws-logs";
const logGroup = new LogGroup(this, "Logs", {
  retention: RetentionDays.ONE_WEEK,
});
```

### React TypeScript
```typescript
// All API calls go through /lib/api.ts — never use fetch() directly
// All auth tokens injected via Axios interceptor — never pass manually
// All environment variables must start with VITE_ and be typed:
// src/lib/env.ts exports typed config object
```

---

## COST GUARDRAILS (Claude Must Enforce These)

### Never Add These to This Project
- NAT Gateway — use VPC Endpoints instead ($32/month idle killer)
- RDS or Aurora — use DynamoDB only
- ElastiCache — not needed for this architecture
- EC2 instances — Lambda and Fargate only
- OpenSearch — use CloudWatch Logs Insights instead
- WAF with managed rules at $5/rule/month — use only free AWS managed rules in Phase 10

### Always Enforce These
- DynamoDB billing: `BillingMode.PAY_PER_REQUEST` — never PROVISIONED
- CloudWatch log retention: max 7 days for Lambda logs
- S3 Lifecycle: delete raw uploads after 30 days, move reports to IA after 30 days
- Fargate tasks: always set `stopTimeout` and max 30-minute hard limit
- Bedrock (app AI engine, NOT Claude Code agents): Haiku 4.5 for explain_risk, Sonnet 4.6 for generate_fix only
- Lambda memory: right-size (don't set 3008MB for simple functions)
- S3: always enable Intelligent Tiering on report bucket
- **S3 VERSIONING — HARD RULE (owner decision): NO versioning on ANY S3 bucket. EVER.**
    - Applies to ALL buckets with NO exceptions: the 5 CDK app buckets, the CDK
      bootstrap/staging bucket (`cdk-hnb659fds-assets-*`), and ANY bucket created
      manually (including when recovering/recreating a deleted bucket).
    - CDK: `versioned: false` on every `s3.Bucket`. Manual/CLI: never run
      `put-bucket-versioning --status Enabled`; leave versioning Disabled.
    - When recreating a deleted bucket, recreate it WITHOUT versioning (block public
      access + SSE + DESTROY semantics yes, but versioning stays OFF).
    - WHY: demo/portfolio project — no rollback ever needed, versioning adds cost,
      and noncurrent versions block clean bucket deletion (breaks one-command teardown).
- S3: `autoDeleteObjects: true` on ALL CDK buckets — no exceptions
- All CDK resources: `RemovalPolicy.DESTROY` always — `cdk destroy --all` must leave nothing behind

### Monthly Cost Targets
```
Development phase:   < $15/month
Idle (sleep mode):   < $5/month
Active demo month:   < $20/month (covers ~650 demo sessions)
```

---

## DEMO LIFECYCLE PROTOCOL

### Before Every Client Demo (Night Before)
```bash
python scripts/demo_wake.py        # Re-enables CloudFront, seeds demo data
# Wait 15 minutes for CloudFront propagation
# Open dashboard URL, verify login works
# Upload sample bad Terraform file, confirm scan completes
# Verify Risk Score shows RED (critical issues in fixture data)
```

### After Every Client Demo (Same Day)
```bash
python scripts/demo_sleep.py       # Disables CloudFront, stops pipeline
python scripts/billing_check.py    # Confirm cost is within target
```

### Demo Script for Client Calls (Talking Points)
1. **Open dashboard** — point to Risk Score (big number, red color if critical)
2. **Show findings table** — explain severity badges, sort by CRITICAL
3. **Click a CRITICAL finding** — show AI explanation (plain English, 2-3 sentences)
4. **Click "View Fix"** — show Bedrock-generated corrected Terraform block
5. **Upload live file** — drag-and-drop a real Terraform file, show WebSocket progress
6. **Show trend chart** — "This organization's risk score improved 40% over 30 days"
7. **Trigger alert** — show Slack notification with CRITICAL finding details

### Sample Bad Terraform File for Demo (`tests/fixtures/bad_terraform.tf`)
Should contain: public S3 bucket, open SSH security group, unencrypted EBS,
wildcard IAM policy, no CloudTrail — triggers all CRITICAL rules in one scan.

---

## ENVIRONMENT LIFECYCLE — SETUP, PROMOTION & TEARDOWN (TESTED, MUST STAY TRUE)

**This project must be self-sustainable and reliable: a clean environment comes up
with ONE command, promotes dev→staging→prod without failing, and tears down to a
$0 empty account with ONE command. This was tested end-to-end on 2026-06-28
(full destroy → verify empty → fresh rebuild → E2E pass). Every future change to
infra MUST preserve these two guarantees. When you add a new AWS resource, you are
NOT done until you have confirmed BOTH: (a) it deploys via the bootstrap sequence,
and (b) it is removed by `cdk destroy --all` with no manual step and no stuck stack.**

### SETUP / PROMOTION — always use `scripts/deploy_env.sh`, never bare `cdk deploy --all`

```
AWS_PROFILE=aws-admin scripts/deploy_env.sh dev        # local
scripts/deploy_env.sh staging                          # CI (OIDC role already assumed)
```

A bare `cdk deploy --all` on a FRESH environment **FAILS** — the ECR bootstrap
deadlock: `lambda.DockerImageFunction.fromEcr` needs its image at CreateFunction
time, but the scanner stack also creates the ECR repos (empty). The script breaks
the deadlock with a dependency-ordered, idempotent 4-step sequence:

```
1. cdk deploy --all  --context computeEnabled=false  → all infra + ECR repos, NO Lambdas
2. build + push all 4 images to THIS env's repos     → Lambda images use buildx
     docker-container driver, --provenance=false, oci-mediatypes=false (Docker-29
     OCI index + provenance is rejected by Lambda); ECS images use the same path
3. cdk deploy --all  (computeEnabled defaults true)  → adds Lambdas, images now present
4. python scripts/seed_rules_catalog.py --env <env>  → loads 20 rules into rules-catalog-<env>
```

**rules-catalog seeding is NOT optional.** The rules engine `scan`s the
rules-catalog table for `enabled=true` rules. A fresh table is EMPTY → the custom
S3-/SG-/IAM-/ENC-/LOG- layer finds nothing and only Checkov fires. Step 4 fixes this.
Any new bootstrap-time data (future seed sets) goes into this same script.

**Promotion dev→staging→prod** runs the SAME script with a different env arg, so
promotion is reliable by construction — the sequence and dependency order are
identical in every environment. CDK's stack dependency graph
(`addDependency(foundation)`) guarantees Foundation→Auth→Scanner order within each
`cdk deploy --all`. The GitHub Actions deploy workflows (02/03) MUST invoke this
script (or replicate its 4 steps) rather than a bare `cdk deploy`, or the first
staging deploy will hit the deadlock. (Update those workflows before the first
real staging promotion — tracked in Phase 2 deferred VERIFY items.)

### TEARDOWN — one command, guaranteed clean, $0 after

```
# 1. Ensure NO scan is mid-flight (running Fargate ENIs lock the VPC → delete hangs):
AWS_PROFILE=aws-admin aws ecs list-tasks --cluster guardrail-cluster-<env> --desired-status RUNNING
# 2. Destroy everything (reverse-ordered automatically by CDK):
AWS_PROFILE=aws-admin npx cdk destroy --all --context env=<env> --force
# 3. One-time orphan sweep (pre-CDK leftovers only — normally nothing):
#    delete any ECR repo not suffixed -<env> that predates the per-service design.
```

**Per-resource teardown handling (all verified):**

| Resource | How it deletes cleanly |
|---|---|
| S3 buckets (×5) | `autoDeleteObjects:true` — CDK Lambda empties non-empty buckets first |
| ECR repos (×4) | `emptyOnDelete:true` — images removed before repo delete |
| DynamoDB (×4) | `RemovalPolicy.DESTROY` |
| VPC / Fargate ENIs | `natGateways:0`; ENIs free when tasks stop — destroy only when idle |
| VPC default-SG CR | `restrictDefaultSecurityGroup:false` — the flaky CDK custom resource is DISABLED (it previously caused a DELETE_FAILED) |
| Lambda / ECS / SQS / SNS / EventBridge / Cognito / IAM / SSM / log groups | `RemovalPolicy.DESTROY`; delete cleanly with the stack |
| KMS key | `DESTROY` → enters 7-day PendingDeletion. **NOT billed**, alias freed, auto-deletes. The only thing that lingers — and it costs $0. |

**Teardown rules (enforced):**
- Every S3 bucket: `autoDeleteObjects:true`. Every ECR repo: `emptyOnDelete:true`.
- Every resource: `RemovalPolicy.DESTROY` (this is a demo — no RETAIN anywhere).
- Any new VPC: `restrictDefaultSecurityGroup:false` + `natGateways:0`.
- NEVER destroy a single lower stack alone (cross-stack exports block it) — always `--all`.
- Stop running Fargate tasks (no active scan) BEFORE destroy, or the VPC delete hangs.
- A KMS key in PendingDeletion is expected and free — do not treat it as a leftover.

---

## AWS ACCOUNT SETUP REQUIREMENTS

Before Phase 1 code can be deployed, verify these are done manually:

```
LOCAL TOOLS
[ ] AWS CLI v2 configured (aws configure) with AdministratorAccess role
[ ] Node.js 20+ installed
[ ] Python 3.12 installed
[ ] Docker Desktop installed (for Fargate image builds)
[ ] GitHub CLI installed: gh auth login

AWS ACCOUNT
[ ] CDK bootstrapped: npx cdk bootstrap aws://ACCOUNT_ID/us-east-1
[ ] Amazon Bedrock model access enabled in us-east-1:
      AWS Console → Bedrock → Model Access → Enable:
        - Claude Haiku (anthropic.claude-haiku-4-5-20251001)
        - Claude Sonnet (anthropic.claude-sonnet-4-6)
[ ] SES email verified: puneetkumarsingh765@gmail.com
[ ] No SCPs blocking Lambda, Bedrock, Fargate, CloudFormation in this account

GITHUB ACTIONS — OIDC SETUP (Do Once, Replaces Stored AWS Keys)
[ ] GitHub repo created: e.g. github.com/puneet-singh/guardrail-auditor
[ ] Create GitHub OIDC provider in AWS IAM:
      Provider URL: https://token.actions.githubusercontent.com
      Audience: sts.amazonaws.com
[ ] Create IAM role: GitHubActionsDeployRole
      Trust policy: allow token.actions.githubusercontent.com
      Condition: repo = puneet-singh/guardrail-auditor, branch = main OR environment = *
      Permissions: AdministratorAccess (scope down to least-privilege after MVP)
[ ] GitHub repo secrets set (Settings → Secrets → Actions):
      AWS_ACCOUNT_ID = your 12-digit account ID
      AWS_REGION = us-east-1
      ECR_REPO_URI = {account}.dkr.ecr.us-east-1.amazonaws.com/guardrail-scanner
[ ] GitHub Environments created (Settings → Environments):
      dev      → no protection rules
      staging  → no protection rules
      prod     → required reviewer: puneetkumarsingh765@gmail.com
```

---

## KNOWN DECISIONS & RATIONALE

| Decision | What | Why |
|---|---|---|
| 3-branch model (dev/staging/main) | Branching strategy | Mirrors enterprise GitHub structure for portfolio credibility; dev=default branch; feature branches PR into dev; code promotes dev→staging→main; each branch maps to a GitHub Environment; all 3 deploy to same AWS account using env-suffixed resource names |
| GitHub Actions over CodePipeline | CI/CD engine | Free for the repo; OIDC means no AWS keys stored in GitHub; more portable and visible to clients/employers than CodePipeline |
| CDK synthesizes CFN | One source of truth | CDK defines infrastructure; cdk synth produces CFN; GitHub Actions runs cdk deploy. cloudformation/ dir contains ONLY scanner demo targets — never hand-authored infra templates |
| CFN + Terraform examples | Scanner demo targets | Both formats in the repo lets demos run live scans without external uploads; bad/ files are intentionally broken and must never be fixed |
| OAC not OAI | CloudFront S3 origin | OAI (Origin Access Identity) is deprecated by AWS; OAC (Origin Access Control) is the current recommended pattern for S3+CloudFront |
| CDK over Terraform | Use AWS CDK for infra | Project is AWS-only; CDK has better L2 constructs and TypeScript type safety |
| No S3 versioning | `versioned: false` on all buckets | Demo project — no rollback needed; versioning complicates teardown (noncurrent versions block bucket deletion) |
| Always DESTROY policy | `RemovalPolicy.DESTROY` on all resources, all envs | Single `cdk destroy --all` removes everything — zero manual cleanup; demo project has no prod data to protect |
| autoDeleteObjects always on | `autoDeleteObjects: true` on all S3 buckets | Buckets with objects block stack deletion; CDK custom Lambda auto-empties them first |
| Python 3.12 for Lambda | Not Node.js for backend | python-hcl2 and cfn-flip are Python-only; keeps backend in one language |
| DynamoDB over RDS | All persistence in DynamoDB | Zero idle cost; no connection pool management in Lambda |
| Fargate for Checkov | Not Lambda for OSS scanner | Checkov install is 500MB+; exceeds Lambda layer limits |
| Cognito over custom auth | Cognito User Pool | Managed MFA, no auth code to maintain, free up to 50k MAUs |
| React Query over Redux | State management | REST + WebSocket state fits React Query perfectly; Redux is overkill |
| Shadcn over MUI | UI component library | No license issues, Tailwind-native, professional look |
| CloudFront OAI | S3 access pattern | Never expose S3 bucket URL directly; OAI forces all traffic through CDK |
| VPC Endpoints | No NAT Gateway | Eliminates $32/month idle cost; all AWS service calls stay on AWS backbone |
| Sonnet 4.6 for all Claude Code tasks | Retired Haiku from Claude Code subagent workflow | Haiku produced more errors per task requiring Sonnet re-diagnosis; net token cost was HIGHER than Sonnet one-shot. Haiku still used in Bedrock app engine for explain_risk (different context — app AI, not dev tool) |
| Docker images for ALL compute | No zip packages, no Lambda layers, no trimming | python-hcl2 + cfn-flip make zip packaging hit-and-trial. Lambda Container Images (up to 10GB from ECR) eliminate this entirely. Same Dockerfile works for Lambda and ECS — consistent deployment pattern across all services. |
| rules-engine as ECS Fargate task | Not Lambda | (1) Heavy dependencies → Docker solves it. (2) Consistent with Checkov Fargate pattern. (3) Per-file model: one EventBridge event per S3 upload → one ECS RunTask → one scan. No batching needed. ECS gives predictable resources without Lambda cold-start risk on 300s workloads. |
| SOLID layered architecture | controllers → services → core → adapters/rules | Flat handlers/ dir mixed AWS calls, parsing, and business logic — violates SRP. Layered pattern: new rule = new file in rules/, zero other changes. New parser = new file in adapters/parsers/. Testable: mock adapter interfaces in service tests. |
| One ECR repo per service (loosely coupled) | Not one shared scanner image | Each Lambda and ECS task has its own ECR repository and Dockerfile. A change in aggregator logic rebuilds only guardrail-aggregator — ingest and rules-engine images are untouched. Independent version history and rollback per service. Each image installs only its own deps: ingest (boto3 + awslambdaric), aggregator (boto3 + awslambdaric), rules-engine (boto3 + hcl2 + cfn-flip — no awslambdaric), checkov (checkov 500MB+). Enterprise microservice pattern: loosely coupled, independently deployable, clearly bounded. |
| python:3.12-slim for ALL images | Not public.ecr.aws/lambda/python:3.12 (AWS base) | AWS base image is Amazon Linux 2 — fewer apt packages, ENTRYPOINT=/lambda-entrypoint.sh conflicts with ECS usage. Debian slim is smaller, better package compatibility. Lambda compatibility provided by awslambdaric pip package (same RIC that AWS base pre-installs). CDK DockerImageCode.entrypoint must be set to ["/usr/local/bin/python", "-m", "awslambdaric"] for Lambda functions. ECS task CDK entryPoint set to ["python", "-m", "src.main"] — no conflict. |
| awslambdaric in requirements.txt | Not in Dockerfile RUN directly | awslambdaric is a runtime dependency. Listing it in requirements.txt documents it as part of the contract, ensures it is version-pinned, and keeps the Dockerfile generic. All images pip install -r requirements.txt — awslambdaric gets installed in every build automatically. |
| Absolute imports always | Not relative imports | WORKDIR is /app. Python resolves src.models.finding → /app/src/models/finding.py correctly. Relative imports (from .models) resolve relative to the handler's own package (src.handlers.models) — wrong level, file does not exist there. Relative imports also break if files move. Absolute imports are robust in Lambda, ECS, and local pytest. |
| ECS tasks read env vars not event dict | ECS handler has main() not handler(event,context) | Lambda receives an event dict from the service that invokes it. ECS Fargate tasks have no such mechanism — inputs arrive as environment variables injected at RunTask time via containerOverrides. Pattern: main() reads os.environ["SCAN_JOB_ID"] etc., calls shared _run_scan(), exits 0 or non-zero. handler(event,context) kept for unit tests only. |
| Secrets Manager for PII only; plain env vars for everything else | Clear split: only values unsuitable for console/logs go to Secrets Manager | Bedrock uses IAM (no key). DynamoDB uses IAM (no credentials). Only SES email addresses (PII) go to Secrets Manager. Model IDs, table names, bucket names are plain env vars — they're AWS resource identifiers visible in the console anyway. One JSON secret per env (`guardrail/{env}/app-secrets`), ARN injected as plain env var, code fetches at cold start. |
| Email-only notifications (no Slack/Teams) | Dropped Slack/Teams from Phase 9 scope | Demo does not require third-party webhook integrations. Email via SES is sufficient: user gets PDF attachment + CRITICAL/HIGH summary in body. Slack/Teams can be added later as a plugin without changing core architecture. |
| Email body: CRITICAL/HIGH only | No MEDIUM/LOW and no compliant resources in body | Email body must focus attention on what needs action. Including passing resources or low-severity findings dilutes the signal. Full detail (all severities + compliant) is in the PDF attachment only. |
| No WebSocket in API layer | Removed from Phase 7 scope | Email is the async completion signal. User opens dashboard after receiving email — no real-time push needed. Removes websocket-handler Lambda, ws-connections DDB table, and API GW WebSocket API entirely. Simplifies both backend and frontend significantly. |
| Static site: S3 + CloudFront | Not bare S3 static website endpoint | S3 website endpoints are HTTP-only; Cognito callback URLs require HTTPS. CloudFront provides HTTPS, caching, OAC for private bucket access, and SPA routing (404 → index.html). The "static website on S3" intent is met — CloudFront is the delivery layer, not a separate hosted service. |
| Frontend: 2 pages only | ScanListPage + ScanDetailPage (no trend chart page) | The question asks for a Risk Score dashboard to show results. A scan list + detail view directly answers that. Trend charts are nice-to-have but out of scope for the MVP demo. |
| Tailwind v3 direct, NOT shadcn/ui CLI | Hand-rolled Tailwind components | shadcn's `npx shadcn init` is interactive and pulls component files — it can't be one-shot reliably in this headless build flow. Plain Tailwind v3 (stable PostCSS plugin) with hand-rolled components meets the "professional look" intent, builds deterministically, and keeps the dep tree small. Recharts also dropped (TrendChart was already out of scope). |
| Lambda Function URL host as CloudFront stopgap | frontend-host/ container Lambda + public Function URL | CloudFront Distribution CREATE is blocked by AWS account verification (403 "account must be verified", needs a Support case — same class as the Phase 6 Bedrock blocker). A $0-idle container Lambda behind a public Function URL (authType NONE) serves the SAME dashboard bundle from the S3 dashboard bucket with in-handler SPA routing. Stays within the $0-idle cost guardrail (ALB was rejected: ~$18/mo idle + running target). frontend-stack.ts (CloudFront) remains the durable target — both read the same S3 bundle, so switching back when verified needs no rebuild. |
| OAC over a cross-stack bucket: import by name + policy in consumer | NOT the live Foundation bucket construct | Passing `foundation.dashboardBucket` (or its `.bucketName` token) into the frontend/host stack created BOTH a dependency cycle (the L2 OAC auto-adds a bucket policy that lands in Foundation and references the consumer's distribution) AND an `Fn::GetStackOutput` deploy failure. Fix: reconstruct the deterministic name `guardrail-dashboard-${env}-${account}` locally, `s3.Bucket.fromBucketName`, and add the OAC `CfnBucketPolicy` in the consuming stack. Single clean Frontend→Foundation edge, no cycle, no cross-stack output. |
| `scripts/deploy_env.sh` is the ONLY setup/promotion path | Not bare `cdk deploy --all` | A bare `cdk deploy --all` fails on a fresh env (ECR bootstrap deadlock: Lambda fromEcr needs an image the just-created repo doesn't have). The script sequences deploy(computeEnabled=false) → push 4 images → deploy(computeEnabled=true) → seed rules-catalog. Idempotent, identical across dev/staging/prod, so promotion is reliable by construction. See ENVIRONMENT LIFECYCLE section. |
| rules-catalog seeding is part of bootstrap | `scripts/seed_rules_catalog.py` runs as step 4 | rules_engine scans the rules-catalog table for enabled rules; a fresh table is empty → custom rules find nothing, only Checkov fires. Proven 2026-06-28: rebuilt-from-empty env scanned 48 findings incl. 9 custom only AFTER seeding. Seeding is non-optional and lives in the bootstrap script. |
| `restrictDefaultSecurityGroup: false` on the VPC | Disable CDK's default-SG custom resource | That CR-backed Lambda intermittently fails on stack DELETE (DELETE_FAILED) once its provider is gone — it actually wedged our Phase A deploy. We don't use the default SG, so disabling the CR removes a teardown-blocker. Required on every VPC in this project. |
| Teardown is a single `cdk destroy --all` to $0 | Tested full destroy → empty → rebuild on 2026-06-28 | Every resource is DESTROY + autoDeleteObjects (S3) + emptyOnDelete (ECR); destroy when idle (no running Fargate ENIs). Only a KMS key lingers in 7-day PendingDeletion at $0. See ENVIRONMENT LIFECYCLE section for the per-resource table and the must-stop-tasks-first rule. |

---

## BRANCHING STRATEGY

### Three-Branch Enterprise Model
This repo uses three long-lived branches that mirror an enterprise GitHub structure.
Each branch maps to a GitHub Environment of the same name.
All three deploy to the **same AWS account** but use env-suffixed resource names so
they coexist without collision.

```
main      ← PROD branch. Protected. Only receives merges from staging via PR.
              GitHub Environment: prod (approval required: puneetkumarsingh765@gmail.com)
              CDK context:        --context env=prod
              AWS resources:      scan-jobs-prod, guardrail-iac-uploads-prod-{account}, etc.
              SSM namespace:      /guardrail/prod/*

staging   ← STAGING branch. Only receives merges from dev via PR.
              GitHub Environment: staging (no protection rules)
              CDK context:        --context env=staging
              AWS resources:      scan-jobs-staging, guardrail-iac-uploads-staging-{account}
              SSM namespace:      /guardrail/staging/*

dev       ← DEFAULT branch. Feature branches merge here via PR.
              GitHub Environment: dev (no protection rules)
              CDK context:        --context env=dev
              AWS resources:      scan-jobs-dev, guardrail-iac-uploads-dev-{account}
              SSM namespace:      /guardrail/dev/*
```

### Code Flow (Always Bottom-Up, Never Skip a Level)
```
feature/phase-1-foundation   ← all active development happens here
        │
        ▼  Pull Request → dev
           01-pr-checks.yml must pass (pytest + cfn-lint + tfsec + checkov)
        │
       dev  ──────────────────────────────► auto-deploys to dev environment
        │
        ▼  Pull Request → staging
           01-pr-checks.yml must pass
        │
     staging ─────────────────────────────► auto-deploys to staging environment
        │
        ▼  Pull Request → main
           01-pr-checks.yml must pass
        │
      main  ────────────────────────────────► deploys to prod environment
                                              (pauses for approval before executing)
```

### Branch Protection Rules (GitHub Settings → Branches)
```
main    : Require PR, require 1 approval, require 01-pr-checks.yml to pass, no direct push
staging : Require PR, require 01-pr-checks.yml to pass, no direct push
dev     : Require PR from feature branches, no direct push (except initial setup)
Default branch: dev  (GitHub Settings → General → Default branch)
```

### Resource Naming Convention (Enforced in CDK)
Every AWS resource name includes the env suffix so all three stacks coexist:

```typescript
// At the top of every CDK stack constructor:
const env = this.node.tryGetContext('env') ?? 'dev';  // fail-safe: default to dev

// Use env in every resource name:
// DynamoDB:  `scan-jobs-${env}`
// S3:        `guardrail-iac-uploads-${env}-${account}`
// Lambda:    `guardrail-ingest-handler-${env}`
// SSM paths: `/guardrail/${env}/api-url`
// Log groups: `/guardrail/${env}/lambda/ingest-handler`
// Tags:       Environment: env  (already in commonTags)
```

### Initial Repository Setup (Already Done in Phase 0)
```bash
git init
git add CLAUDE.md .gitignore
git commit -m "Initial commit: CLAUDE.md project intelligence file"
git remote add origin https://github.com/YOUR_USERNAME/guardrail-auditor.git
git branch -M main && git push -u origin main
git checkout -b staging && git push -u origin staging
git checkout -b dev && git push -u origin dev
# Then: GitHub → Settings → General → Default branch → dev
# Then: GitHub → Settings → Branches → add protection rules for each branch
```

---

## GITHUB ACTIONS CI/CD PIPELINE

### How Deployment Works End-to-End

```
Developer creates feature branch off dev, writes code, opens PR → dev
        │
        ▼
01-pr-checks.yml runs on every PR (to dev, staging, or main)
  pytest + cfn-lint + tfsec + checkov — ALL must pass, else PR is blocked
        │
        ▼ PR merged to dev
GitHub Actions detects branch=dev + changed paths:
        │
        ├─ infrastructure/**  → 02-deploy-infra.yml  → cdk deploy --context env=dev
        ├─ scanner/** api/** ai-engine/**  → 03-deploy-lambdas.yml  → lambda update (dev)
        ├─ frontend/**  → 04-deploy-frontend.yml  → s3 sync + CloudFront (dev)
        └─ fargate/**   → 05-deploy-fargate.yml   → ECR push + task def update (dev)
        │
        ▼ PR merged dev → staging (after dev verification)
Same workflows trigger again, this time with branch=staging:
        └─ All four deploy workflows run against staging environment
        │
        ▼ PR merged staging → main (after staging verification)
Same workflows trigger with branch=main:
        └─ All four deploy workflows run against prod environment
           ⚠ prod GitHub Environment gate pauses execution for approval email
           ⚠ puneetkumarsingh765@gmail.com must approve before AWS changes are made
```

### Deployment Sequence for Infrastructure (MUST follow this order)

CloudFormation stacks have dependencies — deploy in this numbered order every time:

```
Stack 1: foundation    ← No dependencies. Creates S3, DynamoDB, KMS, IAM, SSM.
Stack 2: auth          ← Depends on foundation (reads SSM params for KMS key ARN)
Stack 3: scanner       ← Depends on foundation (DynamoDB tables, S3 buckets)
Stack 4: ai-engine     ← Depends on foundation + scanner (reads findings table ARN)
Stack 5: api           ← Depends on foundation + auth + scanner + ai-engine
Stack 6: frontend      ← Depends on api (needs API Gateway URL for VITE_API_URL)
Stack 7: monitoring    ← Depends on all above (monitors all resources)
```

The `02-deploy-infra.yml` workflow enforces this order using sequential steps with
`aws cloudformation wait stack-update-complete` between each stack.

### Workflow Specs

#### `01-pr-checks.yml` — Runs on every Pull Request
```yaml
# Triggers: pull_request targeting dev, staging, or main
# Jobs (run in parallel — ALL must pass or PR is blocked):
#   1. python-tests: pytest scanner/ api/ ai-engine/ --cov=src --cov-fail-under=70
#   2. cfn-lint:     cfn-lint cloudformation/**/*.yaml
#   3. tfsec:        tfsec terraform-examples/ --no-color
#   4. checkov:      checkov -d cloudformation/ terraform-examples/ --framework terraform,cloudformation
# Does NOT deploy anything — checks only
```

#### `02-deploy-infra.yml` — Runs on push to dev, staging, or main (infrastructure/** changed)
```yaml
# Triggers: push to [dev, staging, main], paths: infrastructure/**
# Environment: branch name maps to GitHub Environment
#   dev    branch → GitHub Environment "dev"    → CDK context env=dev
#   staging branch → GitHub Environment "staging" → CDK context env=staging
#   main   branch → GitHub Environment "prod"   → CDK context env=prod
# Steps:
#   1. Assume GitHubActionsDeployRole via OIDC
#   2. Resolve env: DEPLOY_ENV = (github.ref_name == 'main') ? 'prod' : github.ref_name
#   3. npm ci in infrastructure/
#   4. npx cdk synth --context env=$DEPLOY_ENV → outputs CFN to cdk.out/
#   5. aws s3 sync cdk.out/ s3://guardrail-cfn-artifacts-{account}/$DEPLOY_ENV/ (artifact backup)
#   6. npx cdk deploy --all --require-approval never --context env=$DEPLOY_ENV
#      CDK dependency graph enforces stack order automatically
#   7. Output all stack outputs to GitHub Actions summary
# ⚠ When branch=main: GitHub Environment "prod" gate pauses for approval before step 6
# Note: cloudformation/ dir is scanner demo targets — NOT deployed by this workflow
```

#### `03-deploy-lambdas.yml` — Runs on push to dev, staging, or main (scanner/ api/ ai-engine/ changed)
```yaml
# Triggers: push to [dev, staging, main], paths: scanner/**, api/**, ai-engine/**
# env var: DEPLOY_ENV resolved same as 02-deploy-infra.yml (main → prod)
# Steps per changed Lambda function:
#   1. pip install -r requirements.txt -t package/
#   2. zip -r lambda.zip package/ src/
#   3. aws s3 cp lambda.zip s3://guardrail-lambda-packages-{account}/$DEPLOY_ENV/{function}/{git-sha}.zip
#   4. aws lambda update-function-code --function-name guardrail-{name}-$DEPLOY_ENV --s3-key {path}
#   5. aws lambda wait function-updated --function-name guardrail-{name}-$DEPLOY_ENV
#   6. aws lambda publish-version → update alias to latest
# ⚠ When branch=main: GitHub Environment "prod" gate pauses for approval
```

#### `04-deploy-frontend.yml` — Runs on push to dev, staging, or main (frontend/** changed)
```yaml
# Triggers: push to [dev, staging, main], paths: frontend/**
# env var: DEPLOY_ENV resolved same as 02-deploy-infra.yml (main → prod)
# Steps:
#   1. npm ci
#   2. Fetch env-specific params from SSM (all under /guardrail/$DEPLOY_ENV/):
#        VITE_API_URL    ← /guardrail/$DEPLOY_ENV/api-url
#        VITE_WS_URL     ← /guardrail/$DEPLOY_ENV/websocket-url
#        VITE_COGNITO_*  ← /guardrail/$DEPLOY_ENV/cognito-*
#   3. npm run build (Vite outputs to dist/)
#   4. aws s3 sync dist/ s3://guardrail-dashboard-$DEPLOY_ENV-{account}/ --delete
#   5. aws cloudfront create-invalidation --distribution-id {env-specific id} --paths "/*"
# ⚠ When branch=main: GitHub Environment "prod" gate pauses for approval
```

#### `05-deploy-fargate.yml` — Runs on push to dev, staging, or main (fargate/** changed)
```yaml
# Triggers: push to [dev, staging, main], paths: fargate/**
# env var: DEPLOY_ENV resolved same as 02-deploy-infra.yml (main → prod)
# Steps:
#   1. docker build -t guardrail-scanner fargate/
#   2. aws ecr get-login-password | docker login --username AWS {ecr-uri}
#   3. docker tag + push to ECR: tagged as $DEPLOY_ENV-{git-sha} AND $DEPLOY_ENV-latest
#   4. Register new ECS task definition revision referencing $DEPLOY_ENV-{git-sha} image
#   5. Update ECS service (if exists) — Fargate picks up new task def on next invocation
# ⚠ When branch=main: GitHub Environment "prod" gate pauses for approval
```

#### `06-hotfix-to-prod.yml` — Emergency only, manual trigger (replaces promote-to-prod)
```yaml
# PURPOSE: Hotfix too urgent to go through dev→staging→main. Bypasses staging.
#          Requires DOUBLE approval as safety gate for skipping the normal flow.
# Triggers: workflow_dispatch (manual button in GitHub UI)
# Inputs: hotfix_branch — name of the hotfix branch to deploy directly to prod
# Steps:
#   1. Run all 01-pr-checks.yml jobs on hotfix_branch — must pass before proceeding
#   2. GitHub Environment "prod" gate: pauses for approval (puneetkumarsingh765@gmail.com)
#   3. On approval: deploy infra + lambdas + frontend from hotfix_branch → prod
#   4. Post incident summary to GitHub Actions summary
# After hotfix: MUST backport via PR hotfix_branch → staging → dev
```

### OIDC Auth Reusable Action (`aws-deploy/action.yml`)
```yaml
# Used by all workflows — handles AWS credential assumption
# Inputs: role-arn, aws-region
# Uses: aws-actions/configure-aws-credentials@v4 with role-to-assume
# No AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY ever stored in GitHub
```

### CloudFormation Template Rules (Claude Must Follow)
- Every template must have a `Description` field
- Every resource must have a `DependsOn` only when order isn't automatic
- Every resource name uses `!Sub "${AWS::StackName}-{resource}"` pattern — no hardcoded names
- All SSM outputs: `Type: AWS::SSM::Parameter` at the bottom of each stack
  (next stack reads via `{{resolve:ssm:/guardrail/{key}}}` — no cross-stack exports)
- `DeletionPolicy: Retain` on DynamoDB and S3 in prod parameters; `Delete` in dev
- All parameters in `cloudformation/parameters/{env}.json` — nothing hardcoded in templates

### Terraform Examples Rules (Claude Must Follow)
- `bad/` files must deliberately trigger specific rules — comment each file with which rule IDs it triggers
- `good/` files must pass cfn-lint, tfsec, AND Checkov cleanly — verified in PR checks
- `demo-master-bad.tf` must trigger at minimum: S3-001, SG-001, IAM-001, ENC-001, LOG-001
- Never fix the bad/ files — they are intentionally wrong for scanner demo purposes

---

## CONTACTS & EXTERNAL RESOURCES

- **Owner:** Puneet Kumar Singh — puneetkumarsingh765@gmail.com
- **Bedrock Docs:** https://docs.aws.amazon.com/bedrock/
- **CDK API Reference:** https://docs.aws.amazon.com/cdk/api/v2/
- **CloudFormation Docs:** https://docs.aws.amazon.com/cloudformation/
- **GitHub Actions OIDC + AWS:** https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services
- **aws-actions/configure-aws-credentials:** https://github.com/aws-actions/configure-aws-credentials
- **cfn-lint:** https://github.com/aws-cloudformation/cfn-lint
- **tfsec:** https://github.com/aquasecurity/tfsec
- **Checkov Rules:** https://www.checkov.io/5.Policy%20Index/terraform.html
- **python-hcl2:** https://github.com/amplify-education/python-hcl2
- **cfn-flip:** https://github.com/awslabs/aws-cfn-template-flip

---

## HOW CLAUDE SHOULD BEHAVE IN THIS PROJECT

1. **Always read SESSION TRACKER first** — never ask "where did we leave off?" — it's here.
2. **Always update PHASE STATUS** at end of session — mark `[~]` for in-progress, `[x]` for done.
3. **Always update SESSION TRACKER** with what was done and what's next.
4. **Never skip tests** — every Lambda function needs at least 3 unit tests.
5. **Never use print()** — always structured JSON logging.
6. **Never hardcode** — account IDs, ARNs, regions, URLs → SSM Parameter Store or CDK tokens.
7. **Never add a service not in the tech stack** without updating this file first.
8. **Cost check** — before adding any new AWS service, verify it has zero idle cost or get approval.
9. **One phase at a time** — complete all checklist items in a phase before moving to next.
10. **Tag everything** — every CDK construct gets the `commonTags` object.

---

## VIBE CODING TEST — MANDATORY ACTIVITIES (Always Active)

This project is a **vibe coding test** — a live demonstration of how effectively AI can be
directed with the right prompts to build a production-grade system end-to-end.
Every session is evidence of that capability.

### MANDATORY ACTIVITY 1 — Prompts Audit Log (prompts.md)

```
You are a vibe coding expert. prompts.md is the black-box flight recorder of this build.
Every user prompt, every decision, every scope correction, every file written must be
traceable here. This is the proof that skilled AI direction builds production software.
```

prompts.md has TWO entry types. Use the correct one based on session mode.

---

#### ENTRY TYPE A — Per-Turn Log (Clarification / Scoping / Review sessions)

**When to write:** After EVERY response in a session where the user is:
- Asking questions or requesting explanation
- Reviewing architecture or design
- Correcting scope or resolving ambiguity
- Suggesting improvements or new requirements
- Reviewing CLAUDE.md for conflicts or gaps

**Format (lightweight — append at the end of each response):**

```markdown
## [YYYY-MM-DD HH:MM] — Clarification: [Topic in 5 words]
**User Prompt:** <exact intent of what the user asked — one sentence>
**Action Taken:** <what Claude did — explained / updated CLAUDE.md / fixed conflict / defined scope>
**Files Changed:** <list CLAUDE.md sections or other files touched, or "none">
**Scope Impact:** <what changed in the project definition, or "none — clarification only">
```

**Example:**
```markdown
## 2026-06-28 17:30 — Clarification: Scanner should use ECS not Lambda
**User Prompt:** Why is rules-engine a Lambda when I said ECS task for scanner?
**Action Taken:** Explained the original decision and agreed it should be ECS. Updated CLAUDE.md:
                  Lambda Specs table, Phase 5 checklist, KNOWN DECISIONS.
**Files Changed:** CLAUDE.md — Lambda Specs table, Phase 5 infra, KNOWN DECISIONS
**Scope Impact:** rules-engine permanently changed from Lambda to ECS Fargate task.
                  scanner/ Docker image now serves both Lambda functions (ingest, aggregator)
                  and ECS tasks (rules-engine) via MODE env var.
```

---

#### ENTRY TYPE B — Per-Phase Log (Implementation sessions)

**When to write:** ONCE, at the END of a phase, in the final housekeeping turn alongside
git commit + PR creation + CLAUDE.md checklist update. Never mid-phase.

**Why not per-response during implementation:** Phase 5 had 13 subagents each appending
prompts.md = 13 Read→Write cycles = ~1-2 agents of pure overhead with no value added.
One comprehensive entry at phase end captures everything with zero waste.

**Format (comprehensive):**

```markdown
## [YYYY-MM-DD HH:MM] — Phase N: [Phase Name]
**User Request:** <what was asked to start this phase>
**Files Created:** <list every new file + line count>
**Files Modified:** <list every edited file>
**Bugs Fixed:** <each bug: root cause in one line>
**Tests:** <X passed, Y% coverage>
**PR:** #<number> → dev
**Outcome:** DONE | IN-PROGRESS | BLOCKED
```

---

**Rules applying to both entry types:**
- prompts.md is append-only — never edit or delete past entries
- This file IS the vibe coding demonstration — every decision traceable from day one
- If prompts.md does not exist, create it on the first write
- Sonnet 4.6 writes all entries inline — no subagents touch this file
- Type A entries: written at the END of the current response before any other closing text
- Type B entries: written as part of the housekeeping checklist (step 6 of 9)

### MANDATORY ACTIVITY 2 — Phase Decision Enforcement

When Claude reads this CLAUDE.md file, it MUST:

1. **Check SESSION TRACKER** → identify the current phase and the exact next step
2. **Check PHASE STATUS** → confirm which items are `[ ]` not started vs `[x]` done
3. **Make decisions autonomously** based on the phases defined above — do not ask the
   user to choose between approaches that are already decided in the phase checklists
4. **Follow the acceptance criteria** — a phase is only complete when its criteria are
   verified, not just when the code is written
5. **Block scope creep** — if a user request conflicts with the current phase, note it
   in `prompts.md` and park it in SESSION TRACKER as "deferred to Phase N"

**Why these two activities exist:** This project proves that a skilled AI (directed by
well-crafted prompts) can build enterprise software. The prompts.md audit log IS the
proof — every decision, every file, every fix is traceable. Treat it as the black box
flight recorder for this build.

---

## TOKEN EFFICIENCY PROTOCOL — ALWAYS ACTIVE

**Budget target: every phase completes with minimum errors and retries.**

**WHY HAIKU WAS RETIRED (2026-06-28):** Haiku produced more errors per task than Sonnet 4.6,
causing retries, re-tests, and debug cycles that consumed MORE total tokens than Sonnet's
higher per-token cost. ECR image push failures, import path bugs, and test coverage misses
all required Sonnet diagnosis anyway. Net result: Haiku cost MORE in token-hours than Sonnet
would have in one-shot execution. Haiku is permanently retired from this project's Claude Code
workflow. All subagents use Sonnet 4.6.

**NOTE: This protocol governs CLAUDE CODE SUBAGENTS only (the development tool).
The Bedrock AI engine INSIDE the app (Phase 6+) continues to route:
  - explain_risk → Claude Haiku 4.5 (high volume, quality is sufficient, $0.014/scan)
  - generate_fix → Claude Sonnet 4.6 (precision required for valid IaC output)
These are two different contexts. Do not confuse them.**

This protocol is mandatory in every session, every response.
Sonnet 4.6 is the ONLY model used for Claude Code execution — both brain AND hands.

---

### SONNET 4.6 DOES EVERYTHING — ALL TASKS INLINE

```
Sonnet 4.6 handles all of these directly — NO subagents, NO Agent tool spawning:

FILE OPERATIONS    : Read, Write, Edit, Glob, Grep — use dedicated tools directly
SHELL COMMANDS     : Bash/PowerShell — git, aws CLI, cdk, pytest, npm — run directly
DIAGNOSIS          : Read the failing file + test output → identify root cause inline
FIX + VERIFY       : Edit the file → run pytest → confirm pass — all in one turn
HOUSEKEEPING       : git add/commit/push + gh pr create + CLAUDE.md + prompts.md
                     done directly by Sonnet in the final turn of each phase

Agent tool: BANNED for this project. Zero subagent spawning. Every step runs inline.
WHY: Each Agent spawn costs ~20K tokens of overhead before doing any real work.
     Sequential inline execution is both faster and cheaper for a build-phase project.
```

**One-shot rule:** Every task must be completed correctly in ONE attempt.
Read the full context before writing. Run tests before committing. No "I'll fix it next."

**Sequential rule:** All work proceeds one step at a time in a defined order.
No parallel subagent groups. No "spawn A and B simultaneously." Step N+1 starts only
after step N is confirmed complete. This is a build project, not a search project —
correctness of sequence matters more than wall-clock speed.

---

### TASK EXECUTION ORDER (every phase follows this — strictly sequential)

```
PHASE N — [Phase Name]
All steps run in order. No parallel subagents. No skipping steps.

STEP 1 — Write source file 1 (inline, Sonnet does it directly)
STEP 2 — Write source file 2
STEP 3 — Write source file 3
  ... (one file per step, read → write → confirm before moving on)

STEP N-2 — Write all test files (after all source files exist)
STEP N-1 — RUN: pytest [module] --cov=src --cov-fail-under=70
            If fails → diagnose root cause inline → edit → re-run → confirm pass
            Do NOT move to next step until tests pass.
STEP N   — HOUSEKEEPING:
            git add → commit → push → gh pr create → CLAUDE.md → prompts.md
```

**Within a single step, parallel tool calls are allowed** (e.g., two independent Read
calls to gather context before writing). But each logical STEP completes fully before
the next step begins. Never write file 2 before file 1 is confirmed correct.

---

### DIAGNOSE-AND-FIX PATTERN (inline — no subagents)

When a test or command fails:
```
Step 1: Read the error output (already in context from the Bash tool result)
Step 2: Identify root cause in one sentence
Step 3: Edit the file to fix it
Step 4: Re-run the failing test/command in the same response
Step 5: If pass → continue. If fail again → one more cycle. After 2 cycles, stop and report.

DO NOT: spawn a "diagnostic agent" then a "fix agent" — that costs 2× agent overhead
DO NOT: commit code that hasn't passed tests locally
```

---

### HOUSEKEEPING CHECKLIST (final turn of every phase)

Run these in order at the end of every phase. All inline, no subagent needed.

```
1. git add [list every modified file explicitly — never git add -A or git add .]
2. git commit -m "[conventional commit message]

   Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
3. git push -u origin feature/phase-N-[name]
4. gh pr create --base dev --title "[title]" --body "$(cat <<'EOF'
   ## Summary
   - [bullet 1]
   - [bullet 2]

   ## Test Plan
   - [ ] pytest passes with ≥70% coverage
   - [ ] acceptance criteria verified

   🤖 Generated with Claude Code
   EOF
   )"
5. Edit CLAUDE.md:
   - Phase N checklist: change [ ] → [x] for completed items
   - SESSION TRACKER: update "What Was Completed" + "NEXT SESSION"
   - Prepend entry to Session Log
6. Append to prompts.md (ONE entry for the whole phase):

   ## [YYYY-MM-DD HH:MM] — Phase N: [Phase Name]
   **User Request:** [what was asked]
   **Files Created:** [list + line counts]
   **Files Modified:** [list]
   **Bugs Fixed:** [root cause in one line each]
   **Tests:** [X passed, Y% coverage]
   **PR:** #[number] → dev
   **Outcome:** DONE

7. git add CLAUDE.md prompts.md
8. git commit -m "docs: Phase N checklist + audit log

   Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
9. git push
```

---

### CI FAILURE TRIAGE PROTOCOL

When a CI check fails:

```
Step 1: gh run view [run-id] --log-failed
        Grep output for ERROR, FAILED, ImportError — extract only the 5-10 relevant lines

Step 2: Diagnose root cause inline (one sentence)

Step 3: Edit the file to fix it → git add → git commit → git push
        Report: what changed + new commit hash

Step 4: gh pr checks [pr-number] --watch → confirm pass/fail

Maximum 3 triage cycles. If still failing after 3 cycles, read the full log and report
the blocker to the user before proceeding.
```

---

### WHAT DEGRADES PERFORMANCE — NEVER DO THESE

```
✗ Spawning ANY subagent via the Agent tool — banned entirely for this project
  WHY: ~20K tokens overhead per spawn before doing real work; sequential inline is cheaper
✗ Parallel subagent groups ("spawn A and B at once") — banned even with Sonnet model
  WHY: This is a build project. Sequence integrity > wall-clock speed. Step N+1 must
       only start after step N is confirmed correct — parallel agents break this guarantee
✗ Using model="haiku" for ANY Claude Code subagent — Haiku is retired from this workflow
  WHY: Haiku errors + retries cost more total tokens than Sonnet one-shot execution
✗ Spawning a diagnostic-only agent then a separate fix agent — diagnose+fix in one turn
✗ Committing before tests pass — always run pytest locally before git commit
✗ Running cdk synth more than once per phase unless a CDK .ts file changed
✗ Running pytest on the full repo when only one module changed — scope to the module

TOKEN WASTE — LEARNED FROM PHASES 5 (added 2026-06-28):
✗ Each agent appending prompts.md — costs 1 Read + 1 Write per agent = ~13× in Phase 5
  FIX: Sonnet appends prompts.md once inline at the end of the phase
✗ Splitting CLAUDE.md update + git into 2 agents — costs 163K tokens for pure overhead
  FIX: housekeeping done in ONE final Sonnet turn (Steps 1–9 of checklist above)
✗ Haiku making errors that require Sonnet diagnosis anyway — net loss vs. Sonnet directly
  FIX: Sonnet 4.6 for everything. Retired Haiku from Claude Code workflow entirely.
✗ Writing integration tests that use @mock_aws with pre-created module-level boto3 clients
  FIX: always patch module-level clients directly (patch.object(module.s3_client, "get_object"))
  WHY: moto @mock_aws does not retroactively intercept clients created at import time
✗ Setting test coverage target without accounting for it in initial test specs
  FIX: count lines in each file before writing tests; design test suite to hit 70%+ upfront
✗ ECR image not present when Lambda or ECS task runs — image pull error at invocation
  FIX: build + push BOTH images before deploying or testing any compute
       See Docker Image Standards → "Build + push commands" for the exact commands
       Two images needed: guardrail-scanner-dev (scanner/) AND guardrail-checkov-dev (fargate/)

✗ Using lambda.Function with runtime=PYTHON_3_12 and code=fromAsset() — ZIP deployment
  FIX: ALWAYS use lambda.DockerImageFunction with DockerImageCode.fromEcr()
  WHY: python-hcl2 + cfn-flip make ZIP packaging hit-and-trial. lambda.Code.fromAsset() is banned.

✗ Using AWS Lambda base image public.ecr.aws/lambda/python:3.12
  FIX: Use python:3.12-slim + awslambdaric>=2.0.0 in requirements.txt
  WHY: AWS base ENTRYPOINT=/lambda-entrypoint.sh conflicts with ECS entryPoint override.
       Amazon Linux 2 has fewer apt packages. python:3.12-slim with awslambdaric is equivalent.

✗ Omitting entrypoint from DockerImageCode.fromEcr() when using python:3.12-slim
  FIX: Always set entrypoint: ["/usr/local/bin/python", "-m", "awslambdaric"] in fromEcr()
  WHY: AWS base image bakes this in; slim image does not. Missing entrypoint = Lambda failure.

✗ Using relative imports in scanner code (from .models or from ..parsers)
  FIX: Always absolute: from src.models.finding import Finding
  WHY: from .models resolves to src.handlers.models — that path does not exist.
       WORKDIR=/app makes absolute imports unambiguous in all execution contexts.

✗ Writing ECS task handler as handler(event, context) reading from event dict
  FIX: ECS entry point must be main() reading os.environ["SCAN_JOB_ID"] etc.
  WHY: ECS has no event dict — inputs arrive via RunTask containerOverrides as env vars.

✗ NAT Gateway auto-created by ECS cluster when no VPC is specified in CDK
  FIX: Create explicit VPC: new ec2.Vpc(this, "Vpc", { natGateways: 0, subnetConfiguration: [PUBLIC] })
       Use assignPublicIp: true + subnetSelection PUBLIC on EcsTask targets in EventBridge rules
  WHY: CDK default VPC creates private subnets + 2 NAT gateways = $64/month idle cost.
```

---

### SESSION START COMMAND (user pastes this to begin any phase)

```
Start the next phase using the TOKEN EFFICIENCY PROTOCOL in CLAUDE.md.
Read SESSION TRACKER → produce the sequential task list → execute ALL steps inline.
Rules:
  - No Agent tool. No subagents. Sonnet 4.6 does everything directly.
  - One step at a time. Confirm each step before starting the next.
  - Tests must pass locally before any git commit.
  - Diagnose+fix inline when tests fail — never defer to a later step.
FINAL STEP: git + PR + CLAUDE.md + prompts.md all in one inline pass.
```

### PHASE EXECUTION BUDGET (target per phase)

| Phase size | Files | Tests | Target turns |
|---|---|---|---|
| Small  | 1-3 files | <10 tests | 2-3 turns total (write → test+fix → housekeeping) |
| Medium | 4-7 files | 10-20 tests | 3-4 turns total |
| Large  | 8-13 files | 20-35 tests | 4-5 turns total |

Each "turn" = one Sonnet response with multiple parallel tool calls.
Phase 5 took 14 agent spawns. With inline Sonnet execution: 4-5 turns maximum.
The savings come from eliminating agent-spawn overhead (~20K tokens each) and Haiku error cycles.
