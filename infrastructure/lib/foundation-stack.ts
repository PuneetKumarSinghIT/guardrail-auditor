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
    const removalPolicy = env === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY;

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

    // Allow CloudWatch to use this key (needed for encrypted SNS → alarm integration)
    this.encryptionKey.addToResourcePolicy(new iam.PolicyStatement({
      principals: [new iam.ServicePrincipal('cloudwatch.amazonaws.com')],
      actions: ['kms:GenerateDataKey', 'kms:Decrypt'],
      resources: ['*'],
    }));

    new ssm.StringParameter(this, 'KmsKeyArnParam', {
      parameterName: `/guardrail/${env}/kms-key-arn`,
      stringValue: this.encryptionKey.keyArn,
    });

    // ── S3 Buckets ───────────────────────────────────────────────────

    // 1. iac-uploads — source IaC files; EventBridge enabled for scan trigger
    this.uploadsBucket = new s3.Bucket(this, 'IacUploadsBucket', {
      bucketName: `guardrail-iac-uploads-${env}-${this.account}`,
      versioned: true,
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: this.encryptionKey,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      eventBridgeEnabled: true,
      lifecycleRules: [{
        expiration: cdk.Duration.days(30),
        noncurrentVersionExpiration: cdk.Duration.days(7),
      }],
      removalPolicy,
      autoDeleteObjects: env !== 'prod',
    });

    new ssm.StringParameter(this, 'UploadsBucketParam', {
      parameterName: `/guardrail/${env}/bucket-iac-uploads`,
      stringValue: this.uploadsBucket.bucketName,
    });

    // 2. scan-reports — generated PDF reports; tiered for cost savings
    this.reportsBucket = new s3.Bucket(this, 'ScanReportsBucket', {
      bucketName: `guardrail-scan-reports-${env}-${this.account}`,
      versioned: true,
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: this.encryptionKey,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      lifecycleRules: [{
        transitions: [
          { storageClass: s3.StorageClass.INFREQUENT_ACCESS, transitionAfter: cdk.Duration.days(30) },
          { storageClass: s3.StorageClass.GLACIER, transitionAfter: cdk.Duration.days(90) },
        ],
        noncurrentVersionExpiration: cdk.Duration.days(90),
      }],
      removalPolicy,
      autoDeleteObjects: env !== 'prod',
    });

    new ssm.StringParameter(this, 'ReportsBucketParam', {
      parameterName: `/guardrail/${env}/bucket-scan-reports`,
      stringValue: this.reportsBucket.bucketName,
    });

    // 3. dashboard — static frontend assets served via CloudFront OAC
    this.dashboardBucket = new s3.Bucket(this, 'DashboardBucket', {
      bucketName: `guardrail-dashboard-${env}-${this.account}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      removalPolicy,
      autoDeleteObjects: env !== 'prod',
    });

    new ssm.StringParameter(this, 'DashboardBucketParam', {
      parameterName: `/guardrail/${env}/bucket-dashboard`,
      stringValue: this.dashboardBucket.bucketName,
    });

    // 4. cfn-artifacts — CDK-synthesized CloudFormation templates uploaded by GitHub Actions
    this.cfnArtifactsBucket = new s3.Bucket(this, 'CfnArtifactsBucket', {
      bucketName: `guardrail-cfn-artifacts-${env}-${this.account}`,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      lifecycleRules: [{
        noncurrentVersionExpiration: cdk.Duration.days(90),
        noncurrentVersionsToRetain: 10,
      }],
      removalPolicy,
      autoDeleteObjects: env !== 'prod',
    });

    new ssm.StringParameter(this, 'CfnArtifactsBucketParam', {
      parameterName: `/guardrail/${env}/bucket-cfn-artifacts`,
      stringValue: this.cfnArtifactsBucket.bucketName,
    });

    // 5. lambda-packages — zipped Lambda code uploaded by GitHub Actions
    this.lambdaPackagesBucket = new s3.Bucket(this, 'LambdaPackagesBucket', {
      bucketName: `guardrail-lambda-packages-${env}-${this.account}`,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      lifecycleRules: [{
        expiration: cdk.Duration.days(30),
        noncurrentVersionExpiration: cdk.Duration.days(7),
      }],
      removalPolicy,
      autoDeleteObjects: env !== 'prod',
    });

    new ssm.StringParameter(this, 'LambdaPackagesBucketParam', {
      parameterName: `/guardrail/${env}/bucket-lambda-packages`,
      stringValue: this.lambdaPackagesBucket.bucketName,
    });

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
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: env === 'prod' },
      removalPolicy,
    });

    this.scanJobsTable.addGlobalSecondaryIndex({
      indexName: 'status-index',
      partitionKey: { name: 'status', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'created_at', type: dynamodb.AttributeType.STRING },
    });

    new ssm.StringParameter(this, 'ScanJobsTableParam', {
      parameterName: `/guardrail/${env}/table-scan-jobs`,
      stringValue: this.scanJobsTable.tableName,
    });
    new ssm.StringParameter(this, 'ScanJobsTableArnParam', {
      parameterName: `/guardrail/${env}/table-scan-jobs-arn`,
      stringValue: this.scanJobsTable.tableArn,
    });

    // 2. findings — one item per rule violation found in a scan
    this.findingsTable = new dynamodb.Table(this, 'FindingsTable', {
      tableName: `findings-${env}`,
      partitionKey: { name: 'scan_job_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'finding_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: this.encryptionKey,
      timeToLiveAttribute: 'ttl',
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: env === 'prod' },
      removalPolicy,
    });

    this.findingsTable.addGlobalSecondaryIndex({
      indexName: 'severity-index',
      partitionKey: { name: 'severity', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'scan_job_id', type: dynamodb.AttributeType.STRING },
    });

    new ssm.StringParameter(this, 'FindingsTableParam', {
      parameterName: `/guardrail/${env}/table-findings`,
      stringValue: this.findingsTable.tableName,
    });
    new ssm.StringParameter(this, 'FindingsTableArnParam', {
      parameterName: `/guardrail/${env}/table-findings-arn`,
      stringValue: this.findingsTable.tableArn,
    });

    // 3. rules-catalog — static list of 20 security rules; no TTL
    this.rulesCatalogTable = new dynamodb.Table(this, 'RulesCatalogTable', {
      tableName: `rules-catalog-${env}`,
      partitionKey: { name: 'rule_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: this.encryptionKey,
      removalPolicy,
    });

    new ssm.StringParameter(this, 'RulesCatalogTableParam', {
      parameterName: `/guardrail/${env}/table-rules-catalog`,
      stringValue: this.rulesCatalogTable.tableName,
    });

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

    new ssm.StringParameter(this, 'WsConnectionsTableParam', {
      parameterName: `/guardrail/${env}/table-ws-connections`,
      stringValue: this.wsConnectionsTable.tableName,
    });

    // ── IAM Roles ────────────────────────────────────────────────────

    // Shared Lambda base role — CloudWatch Logs + X-Ray only
    // Each Lambda stack adds function-specific permissions on top of this
    this.lambdaBaseRole = new iam.Role(this, 'LambdaBaseRole', {
      roleName: `guardrail-lambda-base-${env}`,
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AWSXRayDaemonWriteAccess'),
      ],
    });

    // Fargate task role — Checkov scanner container reads IaC from S3, writes findings to DDB via SQS
    this.fargateTaskRole = new iam.Role(this, 'FargateTaskRole', {
      roleName: `guardrail-fargate-task-${env}`,
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    });

    this.uploadsBucket.grantRead(this.fargateTaskRole);
    this.findingsTable.grantWriteData(this.fargateTaskRole);
    this.encryptionKey.grantDecrypt(this.fargateTaskRole);

    new ssm.StringParameter(this, 'LambdaBaseRoleArnParam', {
      parameterName: `/guardrail/${env}/iam-lambda-base-role-arn`,
      stringValue: this.lambdaBaseRole.roleArn,
    });
    new ssm.StringParameter(this, 'FargateTaskRoleArnParam', {
      parameterName: `/guardrail/${env}/iam-fargate-task-role-arn`,
      stringValue: this.fargateTaskRole.roleArn,
    });

    // ── Billing Alarm ────────────────────────────────────────────────
    // Requires "Billing Alerts" enabled in AWS Billing console (one-time manual step)
    // Billing metrics are only published in us-east-1

    const billingTopic = new sns.Topic(this, 'BillingAlertsTopic', {
      topicName: `guardrail-billing-alerts-${env}`,
      masterKey: this.encryptionKey,
    });

    billingTopic.addSubscription(
      new snsSubscriptions.EmailSubscription('puneetkumarsingh765@gmail.com')
    );

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
    new cdk.CfnOutput(this, 'KmsKeyArn', { value: this.encryptionKey.keyArn, exportName: `guardrail-kms-key-arn-${env}` });
    new cdk.CfnOutput(this, 'UploadsBucketName', { value: this.uploadsBucket.bucketName });
    new cdk.CfnOutput(this, 'ReportsBucketName', { value: this.reportsBucket.bucketName });
    new cdk.CfnOutput(this, 'ScanJobsTableName', { value: this.scanJobsTable.tableName });
    new cdk.CfnOutput(this, 'FindingsTableName', { value: this.findingsTable.tableName });
    new cdk.CfnOutput(this, 'LambdaBaseRoleArn', { value: this.lambdaBaseRole.roleArn });
    new cdk.CfnOutput(this, 'FargateTaskRoleArn', { value: this.fargateTaskRole.roleArn });
  }
}
