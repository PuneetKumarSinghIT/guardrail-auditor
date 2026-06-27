import * as cdk from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as ecr from "aws-cdk-lib/aws-ecr";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import { SqsEventSource } from "aws-cdk-lib/aws-lambda-event-sources";
import * as logs from "aws-cdk-lib/aws-logs";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as sqs from "aws-cdk-lib/aws-sqs";
import * as ssm from "aws-cdk-lib/aws-ssm";
import { Construct } from "constructs";

interface ScannerStackProps extends cdk.StackProps {
  scanJobsTable: dynamodb.Table;
  findingsTable: dynamodb.Table;
  rulesCatalogTable: dynamodb.Table;
  uploadBucket: s3.Bucket;
  kmsKey: cdk.aws_kms.Key;
  eventBus: events.EventBus;
}

export class ScannerStack extends cdk.Stack {
  public readonly ingestHandlerFn: lambda.Function;
  public readonly rulesEngineFn: lambda.Function;
  public readonly aggregatorFn: lambda.Function;
  public readonly checkovResultsQueue: sqs.Queue;

  constructor(scope: Construct, id: string, props: ScannerStackProps) {
    super(scope, id, props);

    const env = this.node.tryGetContext("env") ?? "dev";

    const commonTags = {
      Project: "SecurityGuardrailAuditor",
      Environment: env,
      Owner: "puneet-singh",
      CostCenter: "demo-portfolio",
    };

    const removalPolicy = cdk.RemovalPolicy.DESTROY;

    // ── Dead-letter queue ────────────────────────────────────────────────────
    const checkovDlq = new sqs.Queue(this, "CheckovDlq", {
      queueName: `guardrail-checkov-dlq-${env}`,
      retentionPeriod: cdk.Duration.days(14),
      encryptionMasterKey: props.kmsKey,
      removalPolicy,
    });

    // ── SQS: Checkov results from Fargate task ───────────────────────────────
    this.checkovResultsQueue = new sqs.Queue(this, "CheckovResultsQueue", {
      queueName: `guardrail-checkov-results-${env}`,
      visibilityTimeout: cdk.Duration.seconds(120),
      retentionPeriod: cdk.Duration.days(1),
      encryptionMasterKey: props.kmsKey,
      deadLetterQueue: { queue: checkovDlq, maxReceiveCount: 3 },
      removalPolicy,
    });

    // ── Base Lambda execution role ───────────────────────────────────────────
    const lambdaRole = new iam.Role(this, "ScannerLambdaRole", {
      roleName: `guardrail-scanner-lambda-role-${env}`,
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          "service-role/AWSLambdaBasicExecutionRole"
        ),
      ],
    });

    props.kmsKey.grantEncryptDecrypt(lambdaRole);
    props.scanJobsTable.grantReadWriteData(lambdaRole);
    props.findingsTable.grantReadWriteData(lambdaRole);
    props.rulesCatalogTable.grantReadData(lambdaRole);
    props.uploadBucket.grantRead(lambdaRole);
    props.eventBus.grantPutEventsTo(lambdaRole);

    lambdaRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
        resources: ["*"],
      })
    );

    // EVENT_BUS_NAME points to the CUSTOM guardrail bus so Lambda publishes there.
    const commonLambdaEnv: Record<string, string> = {
      SCAN_JOBS_TABLE: props.scanJobsTable.tableName,
      FINDINGS_TABLE: props.findingsTable.tableName,
      RULES_TABLE: props.rulesCatalogTable.tableName,
      UPLOAD_BUCKET: props.uploadBucket.bucketName,
      EVENT_BUS_NAME: props.eventBus.eventBusName,
      CHECKOV_QUEUE_URL: this.checkovResultsQueue.queueUrl,
      POWERTOOLS_SERVICE_NAME: "guardrail-scanner",
      LOG_LEVEL: "INFO",
    };

    // ── Lambda: ingest-handler ───────────────────────────────────────────────
    this.ingestHandlerFn = new lambda.Function(this, "IngestHandler", {
      functionName: `guardrail-ingest-handler-${env}`,
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "scanner.src.handlers.ingest_handler.handler",
      code: lambda.Code.fromAsset("../scanner"),
      memorySize: 256,
      timeout: cdk.Duration.seconds(30),
      role: lambdaRole,
      environment: commonLambdaEnv,
      tracing: lambda.Tracing.ACTIVE,
      logGroup: new logs.LogGroup(this, "IngestHandlerLogs", {
        logGroupName: `/guardrail/${env}/lambda/ingest-handler`,
        retention: logs.RetentionDays.ONE_WEEK,
        removalPolicy,
      }),
    });

    // ── Lambda: rules-engine ─────────────────────────────────────────────────
    this.rulesEngineFn = new lambda.Function(this, "RulesEngine", {
      functionName: `guardrail-rules-engine-${env}`,
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "scanner.src.handlers.rules_engine.handler",
      code: lambda.Code.fromAsset("../scanner"),
      memorySize: 512,
      timeout: cdk.Duration.seconds(300),
      role: lambdaRole,
      environment: commonLambdaEnv,
      tracing: lambda.Tracing.ACTIVE,
      logGroup: new logs.LogGroup(this, "RulesEngineLogs", {
        logGroupName: `/guardrail/${env}/lambda/rules-engine`,
        retention: logs.RetentionDays.ONE_WEEK,
        removalPolicy,
      }),
    });

    // ── Lambda: aggregator ───────────────────────────────────────────────────
    this.aggregatorFn = new lambda.Function(this, "Aggregator", {
      functionName: `guardrail-aggregator-${env}`,
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "scanner.src.handlers.aggregator.handler",
      code: lambda.Code.fromAsset("../scanner"),
      memorySize: 256,
      timeout: cdk.Duration.seconds(60),
      role: lambdaRole,
      environment: commonLambdaEnv,
      tracing: lambda.Tracing.ACTIVE,
      logGroup: new logs.LogGroup(this, "AggregatorLogs", {
        logGroupName: `/guardrail/${env}/lambda/aggregator`,
        retention: logs.RetentionDays.ONE_WEEK,
        removalPolicy,
      }),
    });

    // Aggregator triggered by SQS checkov-results queue
    this.aggregatorFn.addEventSource(
      new SqsEventSource(this.checkovResultsQueue, { batchSize: 10 })
    );
    this.checkovResultsQueue.grantConsumeMessages(lambdaRole);

    // ── ECR repository for Fargate scanner image ─────────────────────────────
    const ecrRepo = new ecr.Repository(this, "ScannerRepo", {
      repositoryName: `guardrail-scanner-${env}`,
      encryptionKey: props.kmsKey,
      imageScanOnPush: true,
      removalPolicy,
      emptyOnDelete: true,
    });

    // ── ECS Cluster ──────────────────────────────────────────────────────────
    const cluster = new ecs.Cluster(this, "ScannerCluster", {
      clusterName: `guardrail-cluster-${env}`,
      containerInsightsV2: ecs.ContainerInsights.ENABLED,
    });

    // ── Fargate task role ────────────────────────────────────────────────────
    const fargateTaskRole = new iam.Role(this, "FargateTaskRole", {
      roleName: `guardrail-fargate-task-role-${env}`,
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
    });

    props.uploadBucket.grantRead(fargateTaskRole);
    this.checkovResultsQueue.grantSendMessages(fargateTaskRole);
    props.kmsKey.grantEncryptDecrypt(fargateTaskRole);

    fargateTaskRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["logs:CreateLogStream", "logs:PutLogEvents"],
        resources: [`arn:aws:logs:${this.region}:${this.account}:log-group:/guardrail/*`],
      })
    );

    // ── Fargate task definition ───────────────────────────────────────────────
    const taskDef = new ecs.FargateTaskDefinition(this, "CheckovTaskDef", {
      family: `guardrail-checkov-${env}`,
      cpu: 256,
      memoryLimitMiB: 512,
      taskRole: fargateTaskRole,
    });

    const fargateLogGroup = new logs.LogGroup(this, "FargateLogs", {
      logGroupName: `/guardrail/${env}/fargate/checkov`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy,
    });

    taskDef.addContainer("checkov-scanner", {
      image: ecs.ContainerImage.fromEcrRepository(ecrRepo, `${env}-latest`),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: "checkov",
        logGroup: fargateLogGroup,
      }),
      environment: {
        SQS_QUEUE_URL: this.checkovResultsQueue.queueUrl,
        AWS_DEFAULT_REGION: this.region,
      },
      stopTimeout: cdk.Duration.seconds(30),
    });

    // ── EventBridge: S3 ObjectCreated → ingest-handler ───────────────────────
    // S3 sends ObjectCreated events to the DEFAULT event bus (not a custom bus),
    // so this rule must be on the default bus. The ingest-handler then publishes
    // ScanRequested onto the CUSTOM guardrail bus (props.eventBus).
    const defaultBus = events.EventBus.fromEventBusName(this, "DefaultBus", "default");
    new events.Rule(this, "S3UploadRule", {
      ruleName: `guardrail-s3-upload-${env}`,
      eventBus: defaultBus,
      eventPattern: {
        source: ["aws.s3"],
        detailType: ["Object Created"],
        detail: {
          bucket: { name: [props.uploadBucket.bucketName] },
        },
      },
      targets: [new targets.LambdaFunction(this.ingestHandlerFn)],
    });

    // ── EventBridge: ScanRequested → rules-engine + Fargate ──────────────────
    // guardrail events are published onto the CUSTOM bus by ingest-handler.
    const scanRequestedRule = new events.Rule(this, "ScanRequestedRule", {
      ruleName: `guardrail-scan-requested-${env}`,
      eventBus: props.eventBus,
      eventPattern: {
        source: ["guardrail"],
        detailType: ["ScanRequested"],
      },
    });

    scanRequestedRule.addTarget(new targets.LambdaFunction(this.rulesEngineFn));

    scanRequestedRule.addTarget(
      new targets.EcsTask({
        cluster,
        taskDefinition: taskDef,
        launchType: ecs.LaunchType.FARGATE,
        assignPublicIp: false,
        containerOverrides: [
          {
            containerName: "checkov-scanner",
            environment: [
              {
                name: "SCAN_JOB_ID",
                value: events.EventField.fromPath("$.detail.scan_job_id"),
              },
              {
                name: "S3_BUCKET",
                value: events.EventField.fromPath("$.detail.s3_bucket"),
              },
              {
                name: "S3_KEY",
                value: events.EventField.fromPath("$.detail.s3_key"),
              },
            ],
          },
        ],
      })
    );

    // ── SSM outputs ───────────────────────────────────────────────────────────
    new ssm.StringParameter(this, "CheckovQueueUrlParam", {
      parameterName: `/guardrail/${env}/checkov-queue-url`,
      stringValue: this.checkovResultsQueue.queueUrl,
    });

    new ssm.StringParameter(this, "EcrRepoUriParam", {
      parameterName: `/guardrail/${env}/ecr-repo-uri`,
      stringValue: ecrRepo.repositoryUri,
    });

    // ── Tags ──────────────────────────────────────────────────────────────────
    Object.entries(commonTags).forEach(([k, v]) => cdk.Tags.of(this).add(k, v));
  }
}
