#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { FoundationStack } from '../lib/foundation-stack';
import { AuthStack } from '../lib/auth-stack';
import { ScannerStack } from '../lib/scanner-stack';
import { AiStack } from '../lib/ai-stack';
import { ApiStack } from '../lib/api-stack';
import { FrontendStack } from '../lib/frontend-stack';
import { FrontendHostStack } from '../lib/frontend-host-stack';
import { MonitoringStack } from '../lib/monitoring-stack';

const app = new cdk.App();

const env = app.node.tryGetContext('env') ?? 'dev';
const awsEnv = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION ?? 'us-east-1',
};

const foundation = new FoundationStack(app, `GuardrailFoundation-${env}`, {
  env: awsEnv,
  description: `Guardrail Auditor - Foundation resources (${env})`,
});

const auth = new AuthStack(app, `GuardrailAuth-${env}`, {
  env: awsEnv,
  description: `Guardrail Auditor - Cognito auth (${env})`,
  encryptionKey: foundation.encryptionKey,
});
auth.addDependency(foundation);

const scanner = new ScannerStack(app, `GuardrailScanner-${env}`, {
  env: awsEnv,
  description: `Guardrail Auditor - Ingestion + scanning engine (${env})`,
  scanJobsTable: foundation.scanJobsTable,
  findingsTable: foundation.findingsTable,
  rulesCatalogTable: foundation.rulesCatalogTable,
  uploadBucket: foundation.uploadsBucket,
  reportsBucket: foundation.reportsBucket,
  kmsKey: foundation.encryptionKey,
  eventBus: foundation.eventBus,
  appSecret: foundation.appSecret,
});
scanner.addDependency(foundation);

const ai = new AiStack(app, `GuardrailAi-${env}`, {
  env: awsEnv,
  description: `Guardrail Auditor - Bedrock AI analysis engine (${env})`,
  scanJobsTable: foundation.scanJobsTable,
  findingsTable: foundation.findingsTable,
  kmsKey: foundation.encryptionKey,
  eventBus: foundation.eventBus,
});
ai.addDependency(foundation);
ai.addDependency(scanner);

const api = new ApiStack(app, `GuardrailApi-${env}`, {
  env: awsEnv,
  description: `Guardrail Auditor - REST API (${env})`,
  scanJobsTable: foundation.scanJobsTable,
  findingsTable: foundation.findingsTable,
  rulesCatalogTable: foundation.rulesCatalogTable,
  uploadsBucket: foundation.uploadsBucket,
  reportsBucket: foundation.reportsBucket,
  kmsKey: foundation.encryptionKey,
  userPool: auth.userPool,
  userPoolClient: auth.userPoolClient,
});
// Api only consumes foundation (tables/buckets) + auth (user pool) exports.
// It does NOT reference scanner/ai resources, so no dependency on them — that
// keeps `cdk deploy GuardrailApi-dev` from pulling the running scanner/ai stacks
// into the deploy set (which under computeEnabled=false would strip their Lambdas).
api.addDependency(foundation);
api.addDependency(auth);

// CloudFront is account-verification-blocked on this account (Distribution CREATE
// returns 403 "account must be verified"), so GuardrailFrontend is GATED OUT of the
// default synth/deploy set. Without this gate, `cdk deploy --all` (local AND the
// 02-deploy-infra CI workflow) fails on this stack every time — both on the 403 and
// on a duplicate /guardrail/{env}/cloudfront-url SSM param (Foundation owns the real
// one). The live dashboard is the frontend-host Lambda Function URL below. Enable the
// CloudFront path the day the account is verified: `--context cloudfrontEnabled=true`.
const cloudfrontEnabled =
  app.node.tryGetContext('cloudfrontEnabled') === 'true';
if (cloudfrontEnabled) {
  const frontend = new FrontendStack(app, `GuardrailFrontend-${env}`, {
    env: awsEnv,
    description: `Guardrail Auditor - CloudFront + S3 dashboard (${env})`,
  });
  // FrontendStack reconstructs the dashboard bucket name internally (no Foundation
  // token), so this explicit dependency is the ONLY Frontend→Foundation edge — it
  // just guarantees the bucket exists before CloudFront fronts it. No cycle.
  frontend.addDependency(foundation);
}

// Stopgap delivery while CloudFront is blocked by AWS account verification:
// a $0-idle Lambda Function URL that serves the same dashboard bundle from S3.
const frontendHost = new FrontendHostStack(app, `GuardrailFrontendHost-${env}`, {
  env: awsEnv,
  description: `Guardrail Auditor - Lambda Function URL SPA host (${env})`,
  kmsKey: foundation.encryptionKey,
});
frontendHost.addDependency(foundation);

// Observability — references pipeline Lambdas by metric dimension (no construct
// import), so it only needs Foundation for the KMS key on its SNS topic.
const monitoring = new MonitoringStack(app, `GuardrailMonitor-${env}`, {
  env: awsEnv,
  description: `Guardrail Auditor - CloudWatch dashboard + alarms (${env})`,
  kmsKey: foundation.encryptionKey,
});
monitoring.addDependency(foundation);
