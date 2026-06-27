# Prompt Audit Log — Enterprise Security Guardrail Auditor
## Evidence of Vibe Coding Session

This file records every user prompt in chronological order, along with what was built as a result.
Maintained by Claude per Lead Architect Rule #2. Part of the git repo as evidence.

---

## Session 1 — 2026-06-28

### Prompt 1
> analyze claude.md file and provide status

**What was done:**
- Read CLAUDE.md and produced a full phase-by-phase status table
- Confirmed Phase 0 and Phase 1 were COMPLETE, Phase 2 not started
- Listed all deployed AWS resources (5 S3 buckets, 4 DynamoDB tables, KMS key, Cognito pool)
- Identified the 3 manual prerequisite steps needed before Phase 2 could begin

---

### Prompt 2
> OK start next phase.

**What was done:**
- Pushed `feature/phase-1-foundation` branch to GitHub
- Created and merged PR #1 (`feature/phase-1-foundation` → `dev`)
- Created `feature/phase-2-cicd` branch
- Wrote all 7 GitHub Actions files:
  - `.github/actions/aws-deploy/action.yml` — reusable OIDC role assumption, no stored AWS keys
  - `.github/workflows/01-pr-checks.yml` — pytest + cfn-lint + tfsec + checkov in parallel
  - `.github/workflows/02-deploy-infra.yml` — CDK synth + deploy on infrastructure/** changes
  - `.github/workflows/03-deploy-lambdas.yml` — path-filtered Lambda packaging → S3 → update-function-code
  - `.github/workflows/04-deploy-frontend.yml` — Vite build with SSM-fetched VITE_* vars + S3 + CF invalidation
  - `.github/workflows/05-deploy-fargate.yml` — Docker build + ECR push (SHA + latest tags) + task def update
  - `.github/workflows/06-hotfix-to-prod.yml` — emergency manual prod deploy, double approval gate
- Updated CLAUDE.md Phase 2 checklist
- Opened PR #2 (`feature/phase-2-cicd` → `dev`)

---

### Prompt 3
> Provide me steps to do all these manual steps.

**What was done:**
- Created ECR repository `guardrail-scanner` via CLI (KMS-encrypted, scan-on-push enabled)
  - URI: `879072872327.dkr.ecr.us-east-1.amazonaws.com/guardrail-scanner`
- Set GitHub secret `ECR_REPO_URI` via CLI
- Provided step-by-step instructions for GitHub UI actions:
  - Branch protection rules for `main`, `staging`, `dev` (via GitHub Rulesets)
  - Setting default branch to `dev`

---

### Prompt 4
> Done all the manual steps.

**What was done:**
- Verified all 3 branch rulesets active: `main_branch_ruleset`, `staging_rule_set`, `dev_rule_set`
- Confirmed default branch = `dev`
- Attempted to merge PR #2 — discovered `01-pr-checks.yml` was failing with 2 bugs:
  1. `setup-python@v5` with `cache: pip` crashes when no `requirements.txt` exists
  2. `tfsec-action` crashes when `terraform-examples/` directory doesn't exist
- Fixed both bugs in `01-pr-checks.yml`:
  - Removed `cache: pip` from all `setup-python` steps
  - Replaced `tfsec-action` with inline curl install + directory existence check
  - Added graceful skip logic to pytest (no test files yet), cfn-lint (no CFN dir yet), checkov
- All 4 pr-checks jobs passed (CloudFormation Lint, tfsec, Checkov, pytest)
- Merged PR #2 (`feature/phase-2-cicd` → `dev`)
- Merged PR #3 and PR #4 (CLAUDE.md housekeeping)
- **Phase 2 COMPLETE**

---

### Prompt 5
> Please add this prompt as well in claude.md file this is the system prompt which you have to follow religiously.
> "Lead Architect mode: ON. We are building a Python-based, API-first [Enterprise Security Guardrail Auditor] using a free database and a dashboard.
> Rules:
> 1. No Manual Edits: You provide all logic and fixes. I will not edit any code.
> 2. Audit Log: You must maintain a file named prompts.md. After every turn, update that file (or provide the text block) with the prompt I just used.
> 3. Time-Check: Start a timer. Goal is an MVP in 4-6 hours (Max window: 16h). Report 'Elapsed Time' at the end of every response.
> Acknowledge and let's start."

**What was done:**
- Added `## LEAD ARCHITECT MODE — ALWAYS ON` section to top of CLAUDE.md with all 3 rules verbatim
- Added rules 6 and 7 to the "HOW TO USE THIS FILE" checklist (update prompts.md, report elapsed time)
- Created `prompts.md` (this file) with backfilled entries for prompts 1–4
- Merged via PR #4 to dev

---

### Prompt 6
> I don't want any versioning in S3 bucket I want a infra which can be deleted easily by using CloudFormation template and by using the stack alone no manual intervention is needed from my end for removing any AWS resource once this demo is and testing is done.

**What was done:**
- Updated `infrastructure/lib/foundation-stack.ts`:
  - Removed `versioned: true` from all 5 S3 buckets (iac-uploads, scan-reports, dashboard, cfn-artifacts, lambda-packages)
  - Removed all `noncurrentVersionExpiration` and `noncurrentVersionsToRetain` lifecycle rules (versioning-specific)
  - Changed `autoDeleteObjects: env !== 'prod'` → `autoDeleteObjects: true` on all buckets (unconditional)
  - Changed `removalPolicy` from `env === 'prod' ? RETAIN : DESTROY` → always `DESTROY`
  - Removed `pointInTimeRecoverySpecification` from DynamoDB tables (demo data, no recovery needed)
  - Added `billingTopic.applyRemovalPolicy(DESTROY)` to SNS topic
  - Refactored all 18 SSM parameters to use a `ssmParam()` helper that calls `.applyRemovalPolicy(DESTROY)` (SSM StringParameter does not accept removalPolicy in constructor)
- Updated `infrastructure/lib/auth-stack.ts`:
  - Same `removalPolicy = DESTROY` always
  - Refactored 4 SSM parameters to use `ssmParam()` helper
  - Added `this.identityPool.applyRemovalPolicy(DESTROY)`
- Updated `infrastructure/CLAUDE.md`: added **Teardown Requirements** table + one-command teardown goal
- Updated root `CLAUDE.md`: added 3 new rows to KNOWN DECISIONS table + 2 lines to COST GUARDRAILS
- Verified: `npx cdk synth --context env=dev` passes with zero errors
- Deployed: `npx cdk deploy GuardrailFoundation-dev GuardrailAuth-dev` — both stacks updated successfully

**One-command teardown now works:**
```bash
npx cdk destroy --all --context env=dev --force
# Removes: all S3 buckets (auto-emptied), DynamoDB tables, Cognito pool, SSM params, IAM roles, SNS topic
# Exception: KMS key enters 7-day AWS-enforced pending deletion window
```

---

### Prompt 7
> So note down this infra requirement as well claude.md file for this project.

**What was done:**
- Already incorporated into Prompt 6 changes above:
  - `infrastructure/CLAUDE.md` → **Teardown Requirements** section with locked rules table
  - Root `CLAUDE.md` → KNOWN DECISIONS table + COST GUARDRAILS updates

---

### Prompt 8
> Even correct the infra if made wrong and maintain one prompt.md file. in which you will write all details and all prompts which I have provided to you for this project. So check all your historic chats as well to create this file in chronological order as I need this file as well a part in my git repo as evidence of vibe coding.

**What was done:**
- Rebuilt this file (`prompts.md`) with complete chronological history from Session 1
- Backfilled all 8 prompts with full detail of what was built in response to each
- File is committed to git repo as evidence of the vibe coding session
- Infrastructure verified correct (synth passes, stacks deployed)

---

## Teardown Command Reference

```bash
# Destroy ALL dev resources (zero manual cleanup needed):
cd infrastructure
npx cdk destroy --all --context env=dev --force

# Verify nothing remains:
aws dynamodb list-tables | grep guardrail        # should return empty
aws s3 ls | grep guardrail                       # should return empty
aws ssm get-parameters-by-path --path /guardrail # should return empty
aws cognito-idp list-user-pools --max-results 10 # should not show guardrail pool

# KMS key will show as "Pending deletion" for 7 days — this is AWS-enforced, cannot be bypassed
aws kms list-keys  # key still visible but disabled/pending-deletion
```
