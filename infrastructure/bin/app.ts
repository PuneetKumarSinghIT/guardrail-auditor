#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { FoundationStack } from '../lib/foundation-stack';
import { AuthStack } from '../lib/auth-stack';
import { ScannerStack } from '../lib/scanner-stack';
import { AiStack } from '../lib/ai-stack';
import { ApiStack } from '../lib/api-stack';

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
  kmsKey: foundation.encryptionKey,
  eventBus: foundation.eventBus,
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
