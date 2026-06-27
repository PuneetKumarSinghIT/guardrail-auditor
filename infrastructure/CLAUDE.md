# Infrastructure CDK Rules

## Stack Naming Convention
- Stack IDs: `GuardrailFoundation-${env}`, `GuardrailAuth-${env}`, etc.
- Resource names must always include env suffix: `scan-jobs-${env}`, `guardrail-iac-uploads-${env}-${account}`
- SSM paths: `/guardrail/${env}/{resource-name}` — all env-namespaced, never hardcoded

## CDK Standards (enforced in every stack)

```typescript
// Always resolve env at the top of every constructor:
const env = this.node.tryGetContext('env') ?? 'dev';

// ALWAYS DESTROY — no exceptions, no env check.
// This is a demo/portfolio project. Stack deletion must remove everything
// with zero manual intervention. Never use RemovalPolicy.RETAIN here.
const removalPolicy = cdk.RemovalPolicy.DESTROY;

// Always apply all four tags at stack level (propagates to all resources):
cdk.Tags.of(this).add('Project', 'SecurityGuardrailAuditor');
cdk.Tags.of(this).add('Environment', env);
cdk.Tags.of(this).add('Owner', 'puneet-singh');
cdk.Tags.of(this).add('CostCenter', 'demo-portfolio');
```

## Teardown Requirements (LOCKED — Do Not Change)

These rules were set explicitly by the project owner and must never be reversed:

| Rule | Requirement | Why |
|---|---|---|
| S3 versioning | `versioned: false` on ALL buckets | Demo project — no rollback needed, simplifies teardown |
| S3 auto-delete | `autoDeleteObjects: true` on ALL buckets | Bucket must empty itself on stack delete — no manual s3 rm |
| Removal policy | `RemovalPolicy.DESTROY` on ALL resources | Single `cdk destroy` or CFN stack delete removes everything |
| SSM parameters | `removalPolicy: DESTROY` on every `StringParameter` | Prevents SSM orphans after stack delete |
| SNS topics | `applyRemovalPolicy(DESTROY)` on every Topic | Prevents SNS orphans after stack delete |
| DynamoDB PITR | Disabled — no `pointInTimeRecovery` | Demo data only, no recovery needed |
| KMS key | `RemovalPolicy.DESTROY` — schedules 7-day pending deletion | AWS-enforced minimum; key is disabled immediately |

**One-command teardown goal:**
```bash
npx cdk destroy --all --context env=dev --force
# Expected result: ALL resources deleted. Zero items left in AWS console.
# Exception: KMS key enters 7-day pending deletion (AWS-enforced, cannot bypass).
```

## Stack Deployment Order (must be respected)
1. GuardrailFoundation — S3, DynamoDB, KMS, IAM, SSM
2. GuardrailAuth      — Cognito (depends on Foundation for KMS key)
3. GuardrailScanner   — Lambda + Fargate (depends on Foundation tables/buckets)
4. GuardrailAi        — Bedrock Lambda (depends on Foundation + Scanner)
5. GuardrailApi       — API Gateway (depends on all above)
6. GuardrailFrontend  — CloudFront + S3 (depends on Api for endpoint URLs)
7. GuardrailMonitor   — CloudWatch dashboard + alarms (depends on all above)

## Key Decisions
- DynamoDB: always PAY_PER_REQUEST, never PROVISIONED
- S3: always enforceSSL + blockPublicAccess.BLOCK_ALL, versioned: false, autoDeleteObjects: true
- Removal policy: always DESTROY for all resources, all envs — demo project, no prod data
- Log groups: NOT pre-created in FoundationStack — created inline with each Lambda
  (useCdkManagedLogGroup: true in cdk.json means CDK manages them per-function)
- CloudFront: use OAC (Origin Access Control), never OAI (deprecated)
- No NAT Gateway, no RDS, no ElastiCache — see CLAUDE.md cost guardrails

## Synth + Deploy Commands
```bash
cd infrastructure
npx cdk synth --context env=dev          # verify before every deploy
npx cdk deploy --all --context env=dev --require-approval never
npx cdk deploy --all --context env=staging --require-approval never
npx cdk deploy --all --context env=prod  # pauses for confirmation
```
