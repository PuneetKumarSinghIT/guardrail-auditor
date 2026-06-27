import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as snsSubscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as cloudwatchActions from 'aws-cdk-lib/aws-cloudwatch-actions';

// Helper: create an SSM parameter and immediately apply DESTROY removal policy.
// ssm.StringParameter does not accept removalPolicy in its constructor props.
function ssmParam(scope: Construct, id: string, name: string, value: string): ssm.StringParameter {
  const p = new ssm.StringParameter(scope, id, { parameterName: name, stringValue: value });
  p.applyRemovalPolicy(cdk.RemovalPolicy.DESTROY);
  return p;
}

export class FoundationStack extends cdk.Stack {
  public readonly encryptionKey: kms.Key;
  public readonly uploadsBucket: s3.Bucket;
  public readonly reportsBucket: s3.Bucket;
  public readonly dashboardBucket: s3.Bucket;
  public readonly cfnArtifactsBucket: s3.Bucket;
  public readonly lambdaPackagesBucket: s3.Bucket;
  public readonly scanJobsTable: dynamodb.Table;
  public readonly findingsTable: dynamodb.Table;
  public readonly rulesCatalogTable: dynamodb.Table;
  public readonly wsConnectionsTable: dynamodb.Table;
  public readonly lambdaBaseRole: iam.Role;
  public readonly fargateTaskRole: iam.Role;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const env = this.node.tryGetContext('env') ?? 'dev';

    // Always DESTROY — this is a demo/portfolio project, no production data.
    // Stack deletion removes everything automatically (autoDeleteObjects handles non-empty buckets).
    // Note: KMS key deletion has a mandatory 7-day AWS pending window; everything else is immediate.
    const removalPolicy = cdk.RemovalPolicy.DESTROY;

    cdk.Tags.of(this).add('Project', 'SecurityGuardrailAuditor');
    cdk.Tags.of(this).add('Environment', env);
    cdk.Tags.of(this).add('Owner', 'puneet-singh');
    cdk.Tags.of(this).add('CostCenter', 'demo-portfolio');

    // ── KMS Key ──────────────────────────────────────────────────────
    this.encryptionKey = new kms.Key(this, 'ProjectKey', {
      alias: `alias/guardrail-key-${env}`,
      description: `Guardrail Auditor encryption key (${env})`,
      enableKeyRotation: true,
      removalPolicy,
    });

    this.encryptionKey.addToResourcePolicy(new iam.PolicyStatement({
      principals: [new iam.ServicePrincipal('cloudwatch.amazonaws.com')],
      actions: ['kms:GenerateDataKey', 'kms:Decrypt'],
      resources: ['*'],
    }));

    ssmParam(this, 'KmsKeyArnParam', `/guardrail/${env}/kms-key-arn`, this.encryptionKey.keyArn);

    // ── S3 Buckets ───────────────────────────────────────────────────
    // No versioning on any bucket — demo project, simplifies teardown.
    // autoDeleteObjects: true — CDK deploys a custom Lambda that empties the bucket
    // before CloudFormation deletes it, so stack delete requires zero manual steps.

    // 1. iac-uploads — source IaC files; EventBridge enabled for scan trigger
    this.uploadsBucket = new s3.Bucket(this, 'IacUploadsBucket', {
      bucketName: `guardrail-iac-uploads-${env}-${this.account}`,
      versioned: false,
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: this.encryptionKey,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      eventBridgeEnabled: true,
      lifecycleRules: [{ expiration: cdk.Duration.days(30) }],
      removalPolicy,
      autoDeleteObjects: true,
    });
    ssmParam(this, 'UploadsBucketParam', `/guardrail/${env}/bucket-iac-uploads`, this.uploadsBucket.bucketName);

    // 2. scan-reports — generated PDF reports; tiered for cost savings
    this.reportsBucket = new s3.Bucket(this, 'ScanReportsBucket', {
      bucketName: `guardrail-scan-reports-${env}-${this.account}`,
      versioned: false,
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: this.encryptionKey,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      lifecycleRules: [{
        transitions: [
          { storageClass: s3.StorageClass.INFREQUENT_ACCESS, transitionAfter: cdk.Duration.days(30) },
          { storageClass: s3.StorageClass.GLACIER, transitionAfter: cdk.Duration.days(90) },
        ],
      }],
      removalPolicy,
      autoDeleteObjects: true,
    });
    ssmParam(this, 'ReportsBucketParam', `/guardrail/${env}/bucket-scan-reports`, this.reportsBucket.bucketName);

    // 3. dashboard — static frontend assets served via CloudFront OAC
    this.dashboardBucket = new s3.Bucket(this, 'DashboardBucket', {
      bucketName: `guardrail-dashboard-${env}-${this.account}`,
      versioned: false,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      removalPolicy,
      autoDeleteObjects: true,
    });
    ssmParam(this, 'DashboardBucketParam', `/guardrail/${env}/bucket-dashboard`, this.dashboardBucket.bucketName);

    // 4. cfn-artifacts — CDK-synthesized CloudFormation templates uploaded by GitHub Actions
    this.cfnArtifactsBucket = new s3.Bucket(this, 'CfnArtifactsBucket', {
      bucketName: `guardrail-cfn-artifacts-${env}-${this.account}`,
      versioned: false,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      removalPolicy,
      autoDeleteObjects: true,
    });
    ssmParam(this, 'CfnArtifactsBucketParam', `/guardrail/${env}/bucket-cfn-artifacts`, this.cfnArtifactsBucket.bucketName);

    // 5. lambda-packages — zipped Lambda code uploaded by GitHub Actions
    this.lambdaPackagesBucket = new s3.Bucket(this, 'LambdaPackagesBucket', {
      bucketName: `guardrail-lambda-packages-${env}-${this.account}`,
      versioned: false,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      lifecycleRules: [{ expiration: cdk.Duration.days(30) }],
      removalPolicy,
      autoDeleteObjects: true,
    });
    ssmParam(this, 'LambdaPackagesBucketParam', `/guardrail/${env}/bucket-lambda-packages`, this.lambdaPackagesBucket.bucketName);

    // ── DynamoDB Tables ──────────────────────────────────────────────

    // 1. scan-jobs — one item per uploaded IaC file
    this.scanJobsTable = new dynamodb.Table(this, 'ScanJobsTable', {
      tableName: `scan-jobs-${env}`,
      partitionKey: { name: 'scan_job_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'created_at', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: this.encryptionKey,
      timeToLiveAttribute: 'ttl',
      removalPolicy,
    });
    this.scanJobsTable.addGlobalSecondaryIndex({
      indexName: 'status-index',
      partitionKey: { name: 'status', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'created_at', type: dynamodb.AttributeType.STRING },
    });
    ssmParam(this, 'ScanJobsTableParam',    `/guardrail/${env}/table-scan-jobs`,     this.scanJobsTable.tableName);
    ssmParam(this, 'ScanJobsTableArnParam', `/guardrail/${env}/table-scan-jobs-arn`, this.scanJobsTable.tableArn);

    // 2. findings — one item per rule violation found in a scan
    this.findingsTable = new dynamodb.Table(this, 'FindingsTable', {
      tableName: `findings-${env}`,
      partitionKey: { name: 'scan_job_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'finding_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: this.encryptionKey,
      timeToLiveAttribute: 'ttl',
      removalPolicy,
    });
    this.findingsTable.addGlobalSecondaryIndex({
      indexName: 'severity-index',
      partitionKey: { name: 'severity', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'scan_job_id', type: dynamodb.AttributeType.STRING },
    });
    ssmParam(this, 'FindingsTableParam',    `/guardrail/${env}/table-findings`,     this.findingsTable.tableName);
    ssmParam(this, 'FindingsTableArnParam', `/guardrail/${env}/table-findings-arn`, this.findingsTable.tableArn);

    // 3. rules-catalog — static list of 20 security rules; no TTL
    this.rulesCatalogTable = new dynamodb.Table(this, 'RulesCatalogTable', {
      tableName: `rules-catalog-${env}`,
      partitionKey: { name: 'rule_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: this.encryptionKey,
      removalPolicy,
    });
    ssmParam(this, 'RulesCatalogTableParam', `/guardrail/${env}/table-rules-catalog`, this.rulesCatalogTable.tableName);

    // 4. ws-connections — live WebSocket connectionIds for scan progress push
    this.wsConnectionsTable = new dynamodb.Table(this, 'WsConnectionsTable', {
      tableName: `ws-connections-${env}`,
      partitionKey: { name: 'connection_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: this.encryptionKey,
      timeToLiveAttribute: 'ttl',
      removalPolicy,
    });
    ssmParam(this, 'WsConnectionsTableParam', `/guardrail/${env}/table-ws-connections`, this.wsConnectionsTable.tableName);

    // ── IAM Roles ────────────────────────────────────────────────────
    this.lambdaBaseRole = new iam.Role(this, 'LambdaBaseRole', {
      roleName: `guardrail-lambda-base-${env}`,
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AWSXRayDaemonWriteAccess'),
      ],
    });

    this.fargateTaskRole = new iam.Role(this, 'FargateTaskRole', {
      roleName: `guardrail-fargate-task-${env}`,
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    });
    this.uploadsBucket.grantRead(this.fargateTaskRole);
    this.findingsTable.grantWriteData(this.fargateTaskRole);
    this.encryptionKey.grantDecrypt(this.fargateTaskRole);

    ssmParam(this, 'LambdaBaseRoleArnParam',  `/guardrail/${env}/iam-lambda-base-role-arn`,  this.lambdaBaseRole.roleArn);
    ssmParam(this, 'FargateTaskRoleArnParam',  `/guardrail/${env}/iam-fargate-task-role-arn`, this.fargateTaskRole.roleArn);

    // ── Billing Alarm ────────────────────────────────────────────────
    const billingTopic = new sns.Topic(this, 'BillingAlertsTopic', {
      topicName: `guardrail-billing-alerts-${env}`,
      masterKey: this.encryptionKey,
    });
    billingTopic.applyRemovalPolicy(removalPolicy);
    billingTopic.addSubscription(new snsSubscriptions.EmailSubscription('puneetkumarsingh765@gmail.com'));

    const billingAlarm = new cloudwatch.Alarm(this, 'BillingAlarm', {
      alarmName: `guardrail-billing-${env}`,
      alarmDescription: 'Monthly AWS cost exceeded $20 — review and sleep demo if not in use',
      metric: new cloudwatch.Metric({
        namespace: 'AWS/Billing',
        metricName: 'EstimatedCharges',
        statistic: 'Maximum',
        period: cdk.Duration.hours(6),
        dimensionsMap: { Currency: 'USD' },
      }),
      threshold: 20,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    billingAlarm.addAlarmAction(new cloudwatchActions.SnsAction(billingTopic));

    // ── Stack Outputs ────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'KmsKeyArn',         { value: this.encryptionKey.keyArn, exportName: `guardrail-kms-key-arn-${env}` });
    new cdk.CfnOutput(this, 'UploadsBucketName', { value: this.uploadsBucket.bucketName });
    new cdk.CfnOutput(this, 'ReportsBucketName', { value: this.reportsBucket.bucketName });
    new cdk.CfnOutput(this, 'ScanJobsTableName', { value: this.scanJobsTable.tableName });
    new cdk.CfnOutput(this, 'FindingsTableName', { value: this.findingsTable.tableName });
    new cdk.CfnOutput(this, 'LambdaBaseRoleArn', { value: this.lambdaBaseRole.roleArn });
    new cdk.CfnOutput(this, 'FargateTaskRoleArn',{ value: this.fargateTaskRole.roleArn });
  }
}
