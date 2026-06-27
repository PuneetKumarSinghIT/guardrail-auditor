# Infrastructure CDK Rules

## Stack Naming Convention
- Stack IDs: `GuardrailFoundation-${env}`, `GuardrailAuth-${env}`, etc.
- Resource names must always include env suffix: `scan-jobs-${env}`, `guardrail-iac-uploads-${env}-${account}`
- SSM paths: `/guardrail/${env}/{resource-name}` — all env-namespaced, never hardcoded

## CDK Standards (enforced in every stack)

```typescript
// Always resolve env at the top of every constructor:
const env = this.node.tryGetContext('env') ?? 'dev';

// Always set removal policy based on env:
const removalPolicy = env === 'prod' ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY;

// Always apply all four tags at stack level (propagates to all resources):
cdk.Tags.of(this).add('Project', 'SecurityGuardrailAuditor');
cdk.Tags.of(this).add('Environment', env);
cdk.Tags.of(this).add('Owner', 'puneet-singh');
cdk.Tags.of(this).add('CostCenter', 'demo-portfolio');
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
- S3: always enforceSSL + blockPublicAccess.BLOCK_ALL
- autoDeleteObjects: true only in dev/staging (not prod), paired with DESTROY removal policy
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
