#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { FoundationStack } from '../lib/foundation-stack';
import { AuthStack } from '../lib/auth-stack';
import { ScannerStack } from '../lib/scanner-stack';

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
