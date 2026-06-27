# Enterprise Security Guardrail Auditor
## Project Intelligence File — Read This First, Every Session

---

## LEAD ARCHITECT MODE — ALWAYS ON

```
Lead Architect mode: ON. We are building a Python-based, API-first
[Enterprise Security Guardrail Auditor] using a free database and a dashboard.

Rules:
1. No Manual Edits: You provide all logic and fixes. I will not edit any code.
2. Audit Log: You must maintain a file named prompts.md. After every turn, update
   that file with the prompt just used.
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
4. Update `## SESSION TRACKER` at the END of every session with what was completed
5. Never repeat work already marked DONE in phase status
6. Update `prompts.md` with the user's prompt at the end of every turn
7. Report **Elapsed Time** at the end of every response

---

## PROJECT IDENTITY

**Name:** Enterprise Security Guardrail Auditor
**Owner:** Puneet Kumar Singh (puneetkumarsingh765@gmail.com)
**Purpose:** Portfolio project to attract clients and job offers — must be
             enterprise-grade, visually impressive, and AI-powered.
**Status:** In active development. Started June 2026.
**AWS Account Type:** Personal demo/portfolio account — NOT customer production data.
**Primary Region:** us-east-1
**Secondary Region:** us-west-2 (DR only, implement in Phase 8)

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
├── scanner/                           ← Python 3.12 Lambda functions
│   ├── CLAUDE.md                      ← Scanner-specific rules
│   ├── src/
│   │   ├── handlers/
│   │   │   ├── ingest_handler.py      ← S3/webhook ingestion Lambda
│   │   │   ├── rules_engine.py        ← Custom rules scan Lambda
│   │   │   ├── aggregator.py          ← Merges Lambda + Fargate results
│   │   │   └── report_generator.py    ← PDF report Lambda
│   │   ├── parsers/
│   │   │   ├── terraform_parser.py    ← python-hcl2 based HCL parser
│   │   │   └── cloudformation_parser.py
│   │   └── models/
│   │       └── finding.py             ← Finding dataclass
│   ├── tests/
│   │   └── fixtures/                  ← Sample bad IaC files for testing
│   └── requirements.txt
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
├── api/                               ← API Gateway Lambda handlers
│   ├── CLAUDE.md                      ← API-specific rules
│   ├── src/
│   │   ├── routes/
│   │   │   ├── scans.py               ← POST /scans, GET /scans/{id}
│   │   │   ├── findings.py            ← GET /findings
│   │   │   ├── dashboard.py           ← GET /dashboard/summary
│   │   │   └── reports.py             ← GET /scans/{id}/report
│   │   ├── middleware/
│   │   │   ├── auth.py                ← Cognito JWT validation
│   │   │   └── cors.py                ← CORS headers
│   │   └── websocket/
│   │       └── connection_handler.py  ← WebSocket connect/disconnect/message
│   ├── tests/
│   └── requirements.txt
│
├── frontend/                          ← React + TypeScript dashboard
│   ├── CLAUDE.md                      ← Frontend-specific rules
│   ├── src/
│   │   ├── components/
│   │   │   ├── RiskScoreMeter.tsx     ← Big circular score display
│   │   │   ├── FindingsTable.tsx      ← Sortable findings with severity badges
│   │   │   ├── TrendChart.tsx         ← Recharts line chart for history
│   │   │   ├── AiExplanationPanel.tsx ← Slide-in panel with Bedrock output
│   │   │   ├── ScanUploader.tsx       ← Drag-and-drop IaC file upload
│   │   │   └── ScanProgress.tsx       ← WebSocket-driven progress bar
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── ScanHistory.tsx
│   │   │   └── Login.tsx
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts        ← WebSocket connection hook
│   │   │   └── useScans.ts            ← React Query hooks for API calls
│   │   └── lib/
│   │       ├── api.ts                 ← Axios instance with auth interceptor
│   │       └── auth.ts                ← Cognito Amplify auth wrapper
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
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
├── fargate/                           ← Fargate OSS scanner container
│   ├── Dockerfile
│   ├── scanner_runner.py              ← Runs Checkov, pushes results to SQS
│   └── requirements.txt
│
└── .github/
    ├── workflows/
    │   ├── 01-pr-checks.yml           ← On every PR: pytest + cfn-lint + tfsec + Checkov
    │   ├── 02-deploy-infra.yml        ← On push to main: upload CFN to S3 → deploy stacks in sequence
    │   ├── 03-deploy-lambdas.yml      ← On push to scanner/ api/ ai-engine/: zip → S3 → Lambda update
    │   ├── 04-deploy-frontend.yml     ← On push to frontend/: build → S3 sync → CloudFront invalidate
    │   ├── 05-deploy-fargate.yml      ← On push to fargate/: Docker build → ECR push → task def update
    │   └── 06-promote-to-prod.yml     ← Manual trigger only: promotes staging → prod with approval gate
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
  ✓ aws dynamodb list-tables → shows scan-jobs, findings, rules-catalog, ws-connections
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
        DynamoDB tables (4): scan-jobs, findings, rules-catalog, ws-connections
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
        Per changed Lambda: pip install → zip → s3 cp
                            → lambda update-function-code (name: guardrail-{fn}-$DEPLOY_ENV)
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

  [ ] rules/rules-catalog.json: 20 rules (see ARCHITECTURE SPECS for full list)
        Each rule: rule_id, name, description, severity, category, iac_types, enabled
  [ ] terraform-examples/good/s3-secure.tf: encrypted, versioned, no public access, logging on
  [ ] terraform-examples/good/sg-restricted.tf: no 0.0.0.0/0 on any port
  [ ] terraform-examples/good/iam-least-privilege.tf: scoped actions, no wildcards, no inline
  [ ] terraform-examples/bad/s3-public-bucket.tf: # Triggers: S3-001, S3-002, S3-004
  [ ] terraform-examples/bad/sg-open-ssh.tf: # Triggers: SG-001, SG-002, SG-003
  [ ] terraform-examples/bad/iam-wildcard.tf: # Triggers: IAM-001, IAM-002
  [ ] terraform-examples/bad/unencrypted-resources.tf: # Triggers: ENC-001, ENC-002
  [ ] terraform-examples/bad/demo-master-bad.tf:
        # Triggers: S3-001, SG-001, IAM-001, ENC-001, LOG-001 minimum
        # This is the PRIMARY demo file — one upload triggers all CRITICAL rules
  [ ] cloudformation/bad/public-s3-cfn.yaml: # CFN equivalent of S3 violations
  [ ] cloudformation/bad/open-sg-cfn.yaml: # CFN equivalent of network violations
  [ ] cloudformation/bad/demo-master-bad.yaml:
        # CFN version of all violations — used when client wants CFN demo
  [ ] cloudformation/good/secure-s3-cfn.yaml
  [ ] cloudformation/good/secure-sg-cfn.yaml
  [ ] VERIFY: run all 5 acceptance criteria commands locally

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
  [ ] scanner/src/models/finding.py:
        @dataclass Finding: rule_id, severity, resource_name, resource_type,
                            line_number, code_snippet, scan_job_id, finding_id
  [ ] scanner/src/handlers/ingest_handler.py:
        Triggered by: EventBridge (S3 ObjectCreated on iac-uploads bucket)
        1. Extract bucket + key from event
        2. Validate extension: .tf .hcl .yaml .json .template — reject all others
        3. Generate scan_job_id = str(uuid.uuid4())
        4. Detect iac_type: terraform (if .tf/.hcl) or cloudformation (if .yaml/.json/.template)
        5. Write DynamoDB: scan_job_id, file_name, s3_key, status=QUEUED, iac_type, created_at
        6. Publish EventBridge: source=guardrail, detail-type=ScanRequested,
                                detail={scan_job_id, s3_key, iac_type}
        7. Return 200
  [ ] scanner/requirements.txt: boto3==1.34.*, uuid (stdlib)
  [ ] scanner/tests/fixtures/valid.tf: minimal valid Terraform file
  [ ] scanner/tests/fixtures/invalid.exe: fake binary file
  [ ] scanner/tests/test_ingest.py: 5 tests
        test_valid_tf_creates_job, test_valid_yaml_creates_job,
        test_invalid_extension_rejected, test_missing_s3_key_fails,
        test_eventbridge_event_published

  INFRASTRUCTURE (update scanner-stack.ts):
  [ ] infrastructure/lib/scanner-stack.ts — add:
        Lambda: ingest-handler (Python 3.12, 256MB, 30s, env: table names + bucket names)
        EventBridge rule: source=aws.s3, detail-type=Object Created, bucket=iac-uploads → ingest-handler
        Grant ingest-handler: DynamoDB write on scan-jobs, EventBridge PutEvents
  [ ] npx cdk deploy ScannerStack (partial — only ingest resources deployed now)
  [ ] VERIFY: run acceptance criteria commands above

═══════════════════════════════════════════════════════════════
PHASE 5: Scanning Engine
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
  [ ] scanner/src/parsers/terraform_parser.py:
        Input: S3 object bytes  Output: dict of {resource_type: {resource_name: attrs}}
        Uses python-hcl2. Handles multi-file .tf (single file for MVP).
  [ ] scanner/src/parsers/cloudformation_parser.py:
        Input: S3 object bytes  Output: dict of {ResourceType: {LogicalId: Properties}}
        Uses cfn-flip (handles both JSON and YAML CFN).
  [ ] scanner/src/handlers/rules_engine.py Lambda:
        Triggered by: EventBridge ScanRequested
        1. Load rules from DynamoDB rules-catalog (enabled=true only)
        2. Download IaC file from S3
        3. Parse based on iac_type (terraform_parser or cloudformation_parser)
        4. Apply each rule → produce Finding objects where violations found
        5. Write all findings to DynamoDB findings table
        6. Update scan-jobs: status=SCANNING
        7. Publish EventBridge: RulesEngineDone {scan_job_id, finding_count}
  [ ] fargate/Dockerfile:
        FROM python:3.12-slim
        RUN pip install checkov boto3
        COPY scanner_runner.py .
        CMD ["python", "scanner_runner.py"]
  [ ] fargate/scanner_runner.py:
        Reads from env: SCAN_JOB_ID, S3_BUCKET, S3_KEY, SQS_QUEUE_URL
        Downloads IaC file from S3
        Runs: checkov -f {file} --output json --quiet
        Parses Checkov JSON → Finding objects (maps checkov check_id to our rule_id where possible)
        Sends batch of findings to SQS queue: guardrail-checkov-results
  [ ] scanner/src/handlers/aggregator.py Lambda:
        Triggered by: SQS guardrail-checkov-results
        1. Read findings batch from SQS message
        2. Deduplicate: if same resource+rule exists from rules_engine, skip
        3. Write new findings to DynamoDB
        4. Update scan-jobs: finding_counts={CRITICAL:n, HIGH:n, MEDIUM:n, LOW:n}, status=COMPLETE
        5. Publish EventBridge: ScanComplete {scan_job_id, risk_score_raw}
  [ ] scanner/requirements.txt: add python-hcl2, cfn-flip

  INFRASTRUCTURE (complete scanner-stack.ts):
  [ ] Lambda: rules-engine (512MB, 300s, EventBridge ScanRequested trigger)
  [ ] Lambda: aggregator (256MB, 60s, SQS trigger)
  [ ] SQS queue: guardrail-checkov-results + DLQ (maxReceiveCount=3)
  [ ] ECS Cluster: guardrail-cluster
  [ ] Fargate task definition: guardrail-scanner (0.25 vCPU, 512MB, ECR image)
  [ ] EventBridge rule: ScanRequested → rules-engine Lambda AND ECS RunTask (Fargate)
  [ ] ECR repo + first Docker image pushed via 05-deploy-fargate.yml

  TESTS:
  [ ] scanner/tests/test_terraform_parser.py: 5 tests (valid, empty, nested, multi-resource, malformed)
  [ ] scanner/tests/test_cloudformation_parser.py: 5 tests
  [ ] scanner/tests/test_rules_engine.py: 1 test per rule category (6 tests minimum)
  [ ] scanner/tests/test_aggregator.py: 3 tests (dedupe, status update, event publish)
  [ ] VERIFY: upload demo-master-bad.tf → run all acceptance criteria

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

  CODE:
  [ ] ai-engine/src/prompts/explain_risk.txt:
        "You are a cloud security expert. In 2-3 sentences, explain why this
         misconfiguration is dangerous for a developer who may not know security.
         Rule: {rule_id}. Resource: {resource_name}. Code: {code_snippet}"
  [ ] ai-engine/src/prompts/generate_fix.txt:
        "Fix the following {iac_type} resource block to remediate the security issue.
         Return ONLY the corrected code block, no explanation.
         Issue: {finding_description}. Original: {code_snippet}"
  [ ] ai-engine/src/prompts/score_risk.txt:
        (Used internally — score is calculated in code, not by Bedrock. File kept for reference.)
  [ ] ai-engine/src/bedrock_client.py:
        boto3 bedrock-runtime client wrapper
        invoke_model(model_id, prompt, max_tokens) → str
        Model routing: HAIKU for explain_risk (max 300 tokens)
                       SONNET for generate_fix (max 800 tokens)
        Retry on ThrottlingException: exponential backoff, max 3 retries
  [ ] ai-engine/src/analyzer.py Lambda:
        Triggered by: EventBridge ScanComplete
        1. Read all findings for scan_job_id from DynamoDB
        2. For each finding:
             a. Call explain_risk → update finding.ai_explanation
             b. If severity in (CRITICAL, HIGH): call generate_fix → update finding.ai_fix_code
        3. Calculate risk_score: sum(WEIGHTS[f.severity] for f in findings)
             WEIGHTS = {CRITICAL:40, HIGH:20, MEDIUM:5, LOW:1}, cap at 200, normalize to 100
        4. Update scan-jobs: risk_score=score, status=AI_COMPLETE
        5. Publish EventBridge: AIAnalysisComplete {scan_job_id, risk_score}
  [ ] ai-engine/requirements.txt: boto3

  INFRASTRUCTURE:
  [ ] infrastructure/lib/ai-stack.ts:
        Lambda: ai-analyzer (512MB, 300s)
        IAM: bedrock:InvokeModel on Haiku ARN + Sonnet ARN only (not *)
        EventBridge rule: ScanComplete → ai-analyzer Lambda

  TESTS:
  [ ] ai-engine/tests/test_bedrock_client.py: 3 tests (success, throttle+retry, model routing)
  [ ] ai-engine/tests/test_analyzer.py: 5 tests (all findings updated, cost guard, score calc,
        MEDIUM findings skip fix generation, event published on completion)
  [ ] VERIFY: run all acceptance criteria

═══════════════════════════════════════════════════════════════
PHASE 7: API Layer
═══════════════════════════════════════════════════════════════
GOAL: All application data is accessible via authenticated REST API
      and scan progress is streamed via WebSocket.

ACCEPTANCE CRITERIA:
  ✓ curl -X POST /v1/scans (with JWT) → returns {presigned_url, scan_job_id}
  ✓ curl GET /v1/dashboard/summary → returns {risk_score, finding_counts, trend:[7 items]}
  ✓ WebSocket client receives ≥ 3 progress events during a scan (QUEUED, SCANNING, AI_COMPLETE)
  ✓ Request without JWT → 401 Unauthorized
  ✓ pytest api/tests/ → all pass

START COMMANDS:
  mkdir -p api/src/routes api/src/middleware api/src/websocket api/tests

  CODE:
  [ ] api/src/middleware/auth.py:
        Validates Cognito JWT using python-jose
        Raises 401 if token missing, expired, or wrong issuer
  [ ] api/src/middleware/cors.py: CORS headers allowing CloudFront domain
  [ ] api/src/routes/scans.py:
        POST /v1/scans: generate S3 presigned PUT URL (expires 5min), create QUEUED DDB record
        GET  /v1/scans: list scans for current user (paginated, max 50, sorted by created_at desc)
        GET  /v1/scans/{id}: full scan details including all findings
  [ ] api/src/routes/findings.py:
        GET /v1/findings: filter by scan_job_id, severity, dismissed=true/false
  [ ] api/src/routes/dashboard.py:
        GET /v1/dashboard/summary: current risk_score, finding_counts, 7-day trend array
  [ ] api/src/routes/reports.py:
        GET /v1/scans/{id}/report: S3 presigned GET URL for PDF (Phase 11 generates PDF)
  [ ] api/src/websocket/connection_handler.py:
        $connect: save {connectionId, scan_job_id} to ws-connections DDB table
        $disconnect: delete connectionId from ws-connections
        Outbound: ai-analyzer Lambda calls API GW Management API to push progress events
  [ ] api/requirements.txt: boto3, python-jose[cryptography]

  INFRASTRUCTURE:
  [ ] infrastructure/lib/api-stack.ts:
        API Gateway REST API (regional, Cognito User Pool authorizer)
        API Gateway WebSocket API (route selection: action field)
        Lambda: api-handler (256MB, 29s) integrated with all REST routes
        Lambda: websocket-handler (128MB, 29s) for $connect/$disconnect
        SSM: /guardrail/api-url, /guardrail/websocket-url

  TESTS:
  [ ] api/tests/test_scans.py: 4 tests (POST success, GET list, GET by id, no-auth-401)
  [ ] api/tests/test_dashboard.py: 3 tests (summary shape, empty state, 7-day trend)
  [ ] api/tests/test_websocket.py: 3 tests (connect saves DDB, disconnect removes, message format)
  [ ] VERIFY: deploy to dev → Postman runs all 7 endpoints successfully

═══════════════════════════════════════════════════════════════
PHASE 8: Frontend Dashboard
═══════════════════════════════════════════════════════════════
GOAL: A browser-accessible dashboard shows Risk Score, findings with
      AI explanations, scan history, and lets users upload IaC files.

ACCEPTANCE CRITERIA (must test in browser — not just build):
  ✓ CloudFront URL loads Login page
  ✓ Login with Cognito credentials succeeds, lands on Dashboard
  ✓ Drag-drop demo-master-bad.tf → progress bar animates → scan results appear
  ✓ Risk Score meter shows correct color (RED for demo file)
  ✓ Click CRITICAL finding → AI explanation panel slides open with explanation text
  ✓ Click "View Fix" → code block shows Bedrock-generated corrected IaC
  ✓ Trend chart renders 7 data points
  ✓ Lighthouse performance score ≥ 80

START COMMANDS:
  cd frontend
  npm create vite@latest . -- --template react-ts
  npm install tailwindcss @shadcn/ui recharts @tanstack/react-query axios aws-amplify

  CODE:
  [ ] src/lib/env.ts: typed env object (VITE_API_URL, VITE_WS_URL, VITE_COGNITO_USER_POOL_ID,
        VITE_COGNITO_CLIENT_ID, VITE_COGNITO_IDENTITY_POOL_ID)
  [ ] src/lib/api.ts: Axios instance, baseURL=VITE_API_URL,
        interceptor: attach Cognito JWT to every request Authorization header
  [ ] src/lib/auth.ts: Amplify v6 wrapper (signIn, signOut, getCurrentUser, getIdToken)
  [ ] pages/Login.tsx: email + password form, calls auth.signIn, redirects to Dashboard
  [ ] components/RiskScoreMeter.tsx:
        Circular gauge (SVG), score 0-100
        0-30: green, 31-60: orange, 61-80: red, 81-100: dark red
        Shows score number + label (Low/Medium/High/Critical Risk)
  [ ] components/FindingsTable.tsx:
        Columns: Severity badge, Rule ID, Resource Name, Line Number, Actions
        Sortable by severity (CRITICAL first), filterable by category
        Row actions: "View Fix" button, "Dismiss" button
  [ ] components/TrendChart.tsx:
        Recharts LineChart, X-axis=date (7 days), Y-axis=risk_score
        Color matches current risk level
  [ ] components/AiExplanationPanel.tsx:
        Slide-in drawer (right side), triggered by "View Fix" button
        Shows: finding details, ai_explanation paragraph, ai_fix_code with syntax highlight
  [ ] components/ScanUploader.tsx:
        Drag-and-drop zone (react-dropzone)
        On drop: POST /v1/scans → get presigned URL → PUT file to S3
        Shows file name + "Scan queued" confirmation
  [ ] components/ScanProgress.tsx:
        Connects to WebSocket (useWebSocket hook)
        Renders stepper: QUEUED → SCANNING → AI_ANALYSIS → COMPLETE
        Shows percentage and current step label
  [ ] hooks/useWebSocket.ts: manages WebSocket connection lifecycle
  [ ] hooks/useScans.ts: React Query hooks for all scan-related API calls
  [ ] pages/Dashboard.tsx: assembles RiskScoreMeter + FindingsTable + TrendChart + ScanUploader
  [ ] pages/ScanHistory.tsx: paginated list of past scans with risk scores

  INFRASTRUCTURE:
  [ ] infrastructure/lib/frontend-stack.ts:
        S3 bucket: dashboard (no public access)
        CloudFront OAC (Origin Access Control — NOT OAI, OAI is deprecated)
        CloudFront distribution: HTTPS only, cache policy, error page → index.html
        SSM: /guardrail/cloudfront-dist-id (needed by demo_sleep.py)
  [ ] GitHub Actions 04-deploy-frontend.yml: fetches VITE_* values from SSM during build

  VERIFY: test all 8 acceptance criteria in a real browser before marking done

═══════════════════════════════════════════════════════════════
PHASE 9: Notifications & Observability
═══════════════════════════════════════════════════════════════
GOAL: Critical scan results alert via email and Slack. System health
      is visible in CloudWatch. Every Lambda is traced in X-Ray.

ACCEPTANCE CRITERIA:
  ✓ Upload demo-master-bad.tf → Slack message received within 2 minutes
  ✓ CloudWatch dashboard shows scan-volume, lambda-errors, bedrock-latency widgets
  ✓ X-Ray traces visible for a complete scan flow (ingest → scan → AI → API)
  ✓ Billing alarm tested: manually set threshold to $0.01, verify email received, then restore $20

START COMMANDS:
  # All work in infrastructure/lib/monitoring-stack.ts and new Lambda files

  [ ] infrastructure/lib/monitoring-stack.ts:
        CloudWatch Dashboard "GuardrailHealth":
          Widget 1: scan-jobs completed per hour (DDB Streams metric or custom metric)
          Widget 2: Lambda error rates (all functions)
          Widget 3: Bedrock invocation latency p95
          Widget 4: Fargate task failures
        X-Ray: enable active tracing on ALL Lambda functions (update all Lambda defs)
        Alarms → SNS topic guardrail-ops-alerts → email:
          Lambda error rate > 5% over 5 minutes
          Fargate task exit code non-zero
          Bedrock p95 latency > 10 seconds
  [ ] EventBridge rule: AIAnalysisComplete where risk_score > 80 → SNS guardrail-critical-alerts
  [ ] SNS guardrail-critical-alerts → Lambda slack-notifier + Lambda teams-notifier
  [ ] Lambda: slack-notifier (128MB, 10s):
        Formats Slack Block Kit message: scan summary + risk score + CRITICAL count + dashboard URL
        Posts to SLACK_WEBHOOK_URL from Secrets Manager (/guardrail/slack-webhook-url)
  [ ] Lambda: teams-notifier (128MB, 10s):
        Microsoft Teams Adaptive Card format (same data as Slack)
        Posts to TEAMS_WEBHOOK_URL from Secrets Manager
  [ ] Secrets Manager: /guardrail/slack-webhook-url (create a test Slack app + incoming webhook)
  [ ] Secrets Manager: /guardrail/teams-webhook-url

  VERIFY: run all 4 acceptance criteria

═══════════════════════════════════════════════════════════════
PHASE 10: Demo Lifecycle & README
═══════════════════════════════════════════════════════════════
GOAL: The demo can be fully put to sleep between client calls and
      woken up reliably the night before. README is client-ready.

ACCEPTANCE CRITERIA:
  ✓ python scripts/demo_sleep.py → CloudFront shows Disabled in console within 1 min
  ✓ python scripts/demo_wake.py → dashboard accessible at CloudFront URL within 15 min
  ✓ python scripts/billing_check.py → prints per-service cost breakdown
  ✓ After sleep + 48 hours idle → billing_check.py shows < $5 accumulated
  ✓ Full end-to-end demo rehearsal completes in under 10 minutes

START COMMANDS:
  mkdir scripts

  [ ] scripts/demo_sleep.py:
        1. Read CloudFront dist ID from SSM /guardrail/cloudfront-dist-id
        2. Disable the distribution (not delete — preserves all config)
        3. Write {state: sleeping, timestamp} to SSM /guardrail/demo-state
        4. Print: "Demo sleeping. Idle cost ~$4/month. Run demo_wake.py before next call."
        Note: Lambda/DynamoDB/S3 already cost $0 at idle — nothing else to stop
  [ ] scripts/demo_wake.py:
        1. Re-enable CloudFront distribution
        2. Call seed_demo_data.py
        3. Write {state: awake, timestamp} to SSM /guardrail/demo-state
        4. Print CloudFront URL + "Ready in ~15 minutes"
  [ ] scripts/seed_demo_data.py:
        Write 3 pre-canned scan jobs to DynamoDB (one at each risk level: HIGH/MEDIUM/LOW)
        Write realistic findings with ai_explanation + ai_fix_code pre-populated
        Write 7-day trend data (show improving trend — good demo narrative)
  [ ] scripts/billing_check.py:
        Use Cost Explorer API: get_cost_and_usage for current month
        Group by SERVICE, print table sorted by cost descending
        Print total and warn if > $15
  [ ] README.md (client-facing, public):
        1-paragraph project description (plain English, no jargon)
        Architecture diagram (ASCII)
        Key capabilities: 20+ security rules, AI explanations, real-time progress, Slack alerts
        Tech stack badges (AWS CDK, Python, React, Bedrock)
        How to deploy: 3 commands (clone, cdk bootstrap, push to GitHub)
        Cost breakdown table (idle vs active)
        Screenshots section (placeholder — add real screenshots after demo)

  VERIFY: do full rehearsal of client demo script (7 talking points in DEMO LIFECYCLE section)

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
        rules-engine: 10, ai-analyzer: 5, api-handler: 20, others: 5
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

**MOST RECENT SESSION: June 28, 2026**

### What Was Completed This Session
- Phase 2 CI/CD Pipeline — COMPLETE. All workflows live, PR #2 merged to dev.
- Merged Phase 1 PR (#1: feature/phase-1-foundation → dev)
- Created feature/phase-2-cicd, wrote all 7 GitHub Actions files
- Fixed 01-pr-checks.yml: removed cache:pip (fails without requirements.txt), replaced
    tfsec action with inline curl install + dir-check (action crashes on missing dir)
- PR #2 checks: all 4 jobs passed (CloudFormation Lint, tfsec, Checkov, pytest)
- PR #2 merged to dev (commit: be980bc)
- Branch protection rulesets active: main_branch_ruleset, staging_rule_set, dev_rule_set
- Default branch set to: dev
- ECR repo created: guardrail-scanner (KMS-encrypted, scan-on-push)
- GitHub secrets set: AWS_ACCOUNT_ID, AWS_REGION, ECR_REPO_URI

### NEXT SESSION MUST START HERE
**Phase 3 — IaC Demo Examples**

  1. git checkout dev && git pull origin dev
  2. git checkout -b feature/phase-3-iac-examples
  3. Create directories: rules/ terraform-examples/good/ terraform-examples/bad/ cloudformation/good/ cloudformation/bad/
  4. Write all files per Phase 3 checklist (see below)
  5. Verify: checkov -d terraform-examples/bad/ → ≥ 5 FAILED checks
  6. Verify: checkov -d terraform-examples/good/ → 0 FAILED checks
  7. PR feature/phase-3-iac-examples → dev (01-pr-checks will now run checkov on the new files)

### Session Log (reverse chronological)
```
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

### Lambda Functions — Specs

| Function | Runtime | Memory | Timeout | Trigger | Key Env Vars |
|---|---|---|---|---|---|
| ingest-handler | Python 3.12 | 256MB | 30s | S3 Event / API GW | SCAN_JOBS_TABLE, UPLOAD_BUCKET |
| rules-engine | Python 3.12 | 512MB | 300s | EventBridge | FINDINGS_TABLE, RULES_TABLE |
| ai-analyzer | Python 3.12 | 512MB | 300s | EventBridge | FINDINGS_TABLE, BEDROCK_MODEL_HAIKU, BEDROCK_MODEL_SONNET |
| aggregator | Python 3.12 | 256MB | 60s | SQS | SCAN_JOBS_TABLE, FINDINGS_TABLE |
| report-generator | Python 3.12 | 1024MB | 120s | EventBridge | REPORTS_BUCKET |
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

### API Gateway Endpoints

```
REST API (v1):
  POST   /v1/scans                    → trigger new scan (upload to S3 presigned)
  GET    /v1/scans                    → list scans (paginated, max 50)
  GET    /v1/scans/{scan_job_id}      → get scan details + findings
  GET    /v1/scans/{scan_job_id}/report → S3 presigned URL for PDF
  PATCH  /v1/findings/{finding_id}   → dismiss a finding
  GET    /v1/dashboard/summary        → Risk Score + counts + 7-day trend
  GET    /v1/rules                    → list all rules in catalog

WebSocket API:
  $connect    → store connectionId in DynamoDB
  $disconnect → remove connectionId
  scan-update → push: { scan_job_id, status, progress_pct, message }
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
| Container | Docker | latest | Fargate task |
| Container Registry | ECR | — | AWS native |

---

## CODING STANDARDS (Claude Must Follow These)

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
- Bedrock: use Haiku by default, Sonnet only when fix code generation is needed
- Lambda memory: right-size (don't set 3008MB for simple functions)
- S3: always enable Intelligent Tiering on report bucket
- S3: `versioned: false` and `autoDeleteObjects: true` on ALL buckets — no exceptions
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
