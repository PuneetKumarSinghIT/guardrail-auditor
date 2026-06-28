import * as cdk from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as ec2 from "aws-cdk-lib/aws-ec2";
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
import * as sns from "aws-cdk-lib/aws-sns";
import * as snsSubscriptions from "aws-cdk-lib/aws-sns-subscriptions";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as cloudwatchActions from "aws-cdk-lib/aws-cloudwatch-actions";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import { Construct } from "constructs";

interface ScannerStackProps extends cdk.StackProps {
  scanJobsTable: dynamodb.Table;
  findingsTable: dynamodb.Table;
  rulesCatalogTable: dynamodb.Table;
  uploadBucket: s3.Bucket;
  reportsBucket: s3.Bucket;
  kmsKey: cdk.aws_kms.Key;
  eventBus: events.EventBus;
  appSecret: secretsmanager.Secret;
}

// ─────────────────────────────────────────────────────────────────────────────
// ECR REPO STRATEGY: One repo per service (loose coupling, independent deploys)
//   guardrail-ingest-{env}        ← Lambda: ingest-handler  (boto3 only)
//   guardrail-aggregator-{env}    ← Lambda: aggregator       (boto3 only)
//   guardrail-rules-engine-{env}  ← ECS:    rules-engine     (boto3 + hcl2 + cfn-flip)
//   guardrail-checkov-{env}       ← ECS:    checkov          (checkov ~500MB, separate)
//
// Each service is built and pushed independently. A change in aggregator logic
// only rebuilds guardrail-aggregator — ingest and rules-engine images are untouched.
// ─────────────────────────────────────────────────────────────────────────────

export class ScannerStack extends cdk.Stack {
  // Optional: only created on the compute pass (computeEnabled !== "false").
  // Phase A bootstrap deploy skips them so ECR repos exist before images are pushed.
  public readonly ingestHandlerFn?: lambda.DockerImageFunction;
  public readonly aggregatorFn?: lambda.DockerImageFunction;
  public readonly checkovResultsQueue: sqs.Queue;

  // Expose ECR repo URIs so CI/CD (GitHub Actions) can push images
  public readonly ingestEcrRepo: ecr.Repository;
  public readonly aggregatorEcrRepo: ecr.Repository;
  public readonly rulesEngineEcrRepo: ecr.Repository;
  public readonly checkovEcrRepo: ecr.Repository;
  // Phase 9: report/email/failure Lambdas share ONE image (carries reportlab).
  public readonly reportEcrRepo: ecr.Repository;
  public readonly reportHandlerFn?: lambda.DockerImageFunction;
  public readonly emailHandlerFn?: lambda.DockerImageFunction;
  public readonly failureHandlerFn?: lambda.DockerImageFunction;

  constructor(scope: Construct, id: string, props: ScannerStackProps) {
    super(scope, id, props);

    const env = this.node.tryGetContext("env") ?? "dev";
    const removalPolicy = cdk.RemovalPolicy.DESTROY;

    // ── Two-phase deploy flag ────────────────────────────────────────────────
    // lambda.DockerImageFunction.fromEcr requires the image to exist at
    // CreateFunction time, but this stack also creates the ECR repos — a
    // bootstrap deadlock on first create. ECS task defs do NOT validate images
    // at registration (only at RunTask), so they deploy regardless.
    //   Phase A:  cdk deploy ... --context computeEnabled=false
    //             → creates ECR repos + ECS + SQS + VPC, skips the 2 Lambdas
    //   (push the 4 images)
    //   Phase B:  cdk deploy ...           (default — computeEnabled true)
    //             → adds the ingest + aggregator Lambdas, images now present
    const computeEnabled =
      this.node.tryGetContext("computeEnabled") !== "false";

    const commonTags = {
      Project: "SecurityGuardrailAuditor",
      Environment: env,
      Owner: "puneet-singh",
      CostCenter: "demo-portfolio",
    };

    // ── ECR lifecycle rules (applied to all repos) ───────────────────────────
    const ecrLifecycle: ecr.LifecycleRule[] = [
      { maxImageCount: 10, description: "Keep last 10 tagged images" },
      {
        maxImageAge: cdk.Duration.days(1),
        tagStatus: ecr.TagStatus.UNTAGGED,
        description: "Delete untagged images after 1 day",
      },
    ];

    const ecrDefaults = {
      encryptionKey: props.kmsKey,
      imageScanOnPush: true,
      removalPolicy,
      emptyOnDelete: true,
      lifecycleRules: ecrLifecycle,
    };

    // ── ECR: ingest-handler Lambda ───────────────────────────────────────────
    // Deps: boto3 + awslambdaric only — no parser libs
    // Dockerfile: scanner/ingest/Dockerfile (build context: scanner/)
    this.ingestEcrRepo = new ecr.Repository(this, "IngestRepo", {
      repositoryName: `guardrail-ingest-${env}`,
      ...ecrDefaults,
    });

    // ── ECR: aggregator Lambda ───────────────────────────────────────────────
    // Deps: boto3 + awslambdaric only — SQS consume + DDB write
    // Dockerfile: scanner/aggregator/Dockerfile (build context: scanner/)
    this.aggregatorEcrRepo = new ecr.Repository(this, "AggregatorRepo", {
      repositoryName: `guardrail-aggregator-${env}`,
      ...ecrDefaults,
    });

    // ── ECR: rules-engine ECS task ───────────────────────────────────────────
    // Deps: boto3 + python-hcl2 + cfn-flip — heavier image (parser libs)
    // Dockerfile: scanner/rules_engine/Dockerfile (build context: scanner/)
    this.rulesEngineEcrRepo = new ecr.Repository(this, "RulesEngineRepo", {
      repositoryName: `guardrail-rules-engine-${env}`,
      ...ecrDefaults,
    });

    // ── ECR: checkov ECS task ────────────────────────────────────────────────
    // Deps: checkov (~500MB) + boto3 — kept separate to avoid bloating scanner images
    // Dockerfile: fargate/Dockerfile (build context: fargate/)
    this.checkovEcrRepo = new ecr.Repository(this, "CheckovRepo", {
      repositoryName: `guardrail-checkov-${env}`,
      ...ecrDefaults,
    });

    // ── ECR: report/email/failure Lambdas (Phase 9) ──────────────────────────
    // ONE image (boto3 + reportlab + awslambdaric) shared by all three Lambdas;
    // each Lambda points its DockerImageCode cmd at its own handler.
    // Dockerfile: scanner/report/Dockerfile (build context: scanner/)
    this.reportEcrRepo = new ecr.Repository(this, "ReportRepo", {
      repositoryName: `guardrail-report-${env}`,
      ...ecrDefaults,
    });

    // ── SSM: ECR URIs for CI/CD pipelines ───────────────────────────────────
    new ssm.StringParameter(this, "IngestEcrUriParam", {
      parameterName: `/guardrail/${env}/ecr-ingest-uri`,
      stringValue: this.ingestEcrRepo.repositoryUri,
    });
    new ssm.StringParameter(this, "AggregatorEcrUriParam", {
      parameterName: `/guardrail/${env}/ecr-aggregator-uri`,
      stringValue: this.aggregatorEcrRepo.repositoryUri,
    });
    new ssm.StringParameter(this, "RulesEngineEcrUriParam", {
      parameterName: `/guardrail/${env}/ecr-rules-engine-uri`,
      stringValue: this.rulesEngineEcrRepo.repositoryUri,
    });
    new ssm.StringParameter(this, "CheckovEcrUriParam", {
      parameterName: `/guardrail/${env}/ecr-checkov-uri`,
      stringValue: this.checkovEcrRepo.repositoryUri,
    });
    new ssm.StringParameter(this, "ReportEcrUriParam", {
      parameterName: `/guardrail/${env}/ecr-report-uri`,
      stringValue: this.reportEcrRepo.repositoryUri,
    });

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

    new ssm.StringParameter(this, "CheckovQueueUrlParam", {
      parameterName: `/guardrail/${env}/checkov-queue-url`,
      stringValue: this.checkovResultsQueue.queueUrl,
    });

    // ── Lambda execution role (shared by ingest + aggregator) ────────────────
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
    this.checkovResultsQueue.grantConsumeMessages(lambdaRole);
    // Each Lambda pulls from its own ECR repo
    this.ingestEcrRepo.grantPull(lambdaRole);
    this.aggregatorEcrRepo.grantPull(lambdaRole);

    lambdaRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
        resources: ["*"],
      })
    );

    const commonLambdaEnv: Record<string, string> = {
      SCAN_JOBS_TABLE: props.scanJobsTable.tableName,
      FINDINGS_TABLE: props.findingsTable.tableName,
      RULES_TABLE: props.rulesCatalogTable.tableName,
      UPLOAD_BUCKET: props.uploadBucket.bucketName,
      EVENT_BUS_NAME: props.eventBus.eventBusName,
      CHECKOV_QUEUE_URL: this.checkovResultsQueue.queueUrl,
      LOG_LEVEL: "INFO",
    };

    // ── Lambdas (compute pass only — see two-phase deploy flag above) ────────
    if (computeEnabled) {
      // ── Lambda: ingest-handler ─────────────────────────────────────────────
      // Image: guardrail-ingest-{env} ECR repo
      // entrypoint + cmd: awslambdaric calls ingest_handler.handler(event, context)
      this.ingestHandlerFn = new lambda.DockerImageFunction(
        this,
        "IngestHandler",
        {
          functionName: `guardrail-ingest-handler-${env}`,
          code: lambda.DockerImageCode.fromEcr(this.ingestEcrRepo, {
            tagOrDigest: `${env}-latest`,
            entrypoint: ["/usr/local/bin/python", "-m", "awslambdaric"],
            cmd: ["src.handlers.ingest_handler.handler"],
          }),
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
        }
      );

      // ── Lambda: aggregator ─────────────────────────────────────────────────
      // Image: guardrail-aggregator-{env} ECR repo
      // Triggered by SQS guardrail-checkov-results queue
      this.aggregatorFn = new lambda.DockerImageFunction(this, "Aggregator", {
        functionName: `guardrail-aggregator-${env}`,
        code: lambda.DockerImageCode.fromEcr(this.aggregatorEcrRepo, {
          tagOrDigest: `${env}-latest`,
          entrypoint: ["/usr/local/bin/python", "-m", "awslambdaric"],
          cmd: ["src.handlers.aggregator.handler"],
        }),
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

      this.aggregatorFn.addEventSource(
        new SqsEventSource(this.checkovResultsQueue, { batchSize: 10 })
      );
    }

    // ── VPC: public subnets only, zero NAT gateways ($0 idle cost) ───────────
    // Fargate tasks use assignPublicIp:true to reach ECR/S3 via internet.
    // Phase 11 adds VPC endpoints to remove internet dependency (still zero NAT).
    const vpc = new ec2.Vpc(this, "ScannerVpc", {
      vpcName: `guardrail-vpc-${env}`,
      maxAzs: 2,
      natGateways: 0,
      // TEARDOWN SAFETY: CDK's default RestrictDefaultSecurityGroup custom resource
      // (a CR-backed Lambda that empties the default SG) intermittently fails on
      // stack DELETE — once its backing Lambda is gone the CR can't run, leaving the
      // stack in DELETE_FAILED. We don't use the default SG, so disable the CR
      // entirely. One less moving part that can wedge `cdk destroy`.
      restrictDefaultSecurityGroup: false,
      subnetConfiguration: [
        {
          name: "public",
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
        },
      ],
    });

    // ── ECS Cluster ──────────────────────────────────────────────────────────
    const cluster = new ecs.Cluster(this, "ScannerCluster", {
      clusterName: `guardrail-cluster-${env}`,
      vpc,
      containerInsightsV2: ecs.ContainerInsights.ENABLED,
    });

    // ── Fargate task role (shared by rules-engine + checkov) ─────────────────
    const fargateTaskRole = new iam.Role(this, "FargateTaskRole", {
      roleName: `guardrail-fargate-task-role-${env}`,
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
    });

    props.uploadBucket.grantRead(fargateTaskRole);
    props.findingsTable.grantReadWriteData(fargateTaskRole);
    props.scanJobsTable.grantReadWriteData(fargateTaskRole);
    props.rulesCatalogTable.grantReadData(fargateTaskRole);
    props.eventBus.grantPutEventsTo(fargateTaskRole);
    this.checkovResultsQueue.grantSendMessages(fargateTaskRole);
    props.kmsKey.grantEncryptDecrypt(fargateTaskRole);
    // Each ECS task pulls only from its own repo
    this.rulesEngineEcrRepo.grantPull(fargateTaskRole);
    this.checkovEcrRepo.grantPull(fargateTaskRole);

    fargateTaskRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["logs:CreateLogStream", "logs:PutLogEvents"],
        resources: [
          `arn:aws:logs:${this.region}:${this.account}:log-group:/guardrail/*`,
        ],
      })
    );

    // ── ECS task definition: rules-engine ────────────────────────────────────
    // Image: guardrail-rules-engine-{env} ECR repo
    // 0.5 vCPU / 1 GB — python-hcl2 + cfn-flip are memory-hungry
    // SCAN_JOB_ID, S3_KEY, IAC_TYPE injected per-invocation via RunTask overrides
    const rulesEngineTaskDef = new ecs.FargateTaskDefinition(
      this,
      "RulesEngineTaskDef",
      {
        family: `guardrail-rules-engine-${env}`,
        cpu: 512,
        memoryLimitMiB: 1024,
        taskRole: fargateTaskRole,
      }
    );

    const rulesEngineLogGroup = new logs.LogGroup(this, "RulesEngineLogs", {
      logGroupName: `/guardrail/${env}/ecs/rules-engine`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy,
    });

    rulesEngineTaskDef.addContainer("rules-engine", {
      containerName: "rules-engine",
      image: ecs.ContainerImage.fromEcrRepository(
        this.rulesEngineEcrRepo,
        `${env}-latest`
      ),
      // ECS does not use Lambda RIC — run src.main directly.
      // src/main.py reads MODE=rules_engine → dispatches to rules_engine.main()
      entryPoint: ["python", "-m", "src.main"],
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: "rules-engine",
        logGroup: rulesEngineLogGroup,
      }),
      environment: {
        FINDINGS_TABLE: props.findingsTable.tableName,
        RULES_TABLE: props.rulesCatalogTable.tableName,
        UPLOAD_BUCKET: props.uploadBucket.bucketName,
        EVENT_BUS_NAME: props.eventBus.eventBusName,
        SCAN_JOBS_TABLE: props.scanJobsTable.tableName,
        MODE: "rules_engine",
        AWS_DEFAULT_REGION: this.region,
        // SCAN_JOB_ID, S3_KEY, IAC_TYPE injected per-invocation via RunTask overrides
      },
      stopTimeout: cdk.Duration.seconds(30),
    });

    // ── ECS task definition: checkov ─────────────────────────────────────────
    // Image: guardrail-checkov-{env} ECR repo (500MB+ — kept separate)
    // SCAN_JOB_ID, S3_BUCKET, S3_KEY injected per-invocation via RunTask overrides
    const checkovTaskDef = new ecs.FargateTaskDefinition(
      this,
      "CheckovTaskDef",
      {
        family: `guardrail-checkov-${env}`,
        cpu: 256,
        memoryLimitMiB: 512,
        taskRole: fargateTaskRole,
      }
    );

    const checkovLogGroup = new logs.LogGroup(this, "CheckovLogs", {
      logGroupName: `/guardrail/${env}/ecs/checkov`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy,
    });

    checkovTaskDef.addContainer("checkov-scanner", {
      containerName: "checkov-scanner",
      image: ecs.ContainerImage.fromEcrRepository(
        this.checkovEcrRepo,
        `${env}-latest`
      ),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: "checkov",
        logGroup: checkovLogGroup,
      }),
      environment: {
        SQS_QUEUE_URL: this.checkovResultsQueue.queueUrl,
        AWS_DEFAULT_REGION: this.region,
        // SCAN_JOB_ID, S3_BUCKET, S3_KEY injected via RunTask overrides
      },
      stopTimeout: cdk.Duration.seconds(30),
    });

    // ── EventBridge: S3 ObjectCreated → ingest-handler Lambda ───────────────
    // Compute pass only — depends on the ingest Lambda created above.
    if (computeEnabled) {
      const defaultBus = events.EventBus.fromEventBusName(
        this,
        "DefaultBus",
        "default"
      );
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
        targets: [new targets.LambdaFunction(this.ingestHandlerFn!)],
      });
    }

    // ── EventBridge: ScanRequested → rules-engine + checkov (parallel) ───────
    // Both fire from the same event on the CUSTOM guardrail bus.
    const scanRequestedRule = new events.Rule(this, "ScanRequestedRule", {
      ruleName: `guardrail-scan-requested-${env}`,
      eventBus: props.eventBus,
      eventPattern: {
        source: ["guardrail"],
        detailType: ["ScanRequested"],
      },
    });

    scanRequestedRule.addTarget(
      new targets.EcsTask({
        cluster,
        taskDefinition: rulesEngineTaskDef,
        launchType: ecs.LaunchType.FARGATE,
        assignPublicIp: true,
        subnetSelection: { subnetType: ec2.SubnetType.PUBLIC },
        containerOverrides: [
          {
            containerName: "rules-engine",
            environment: [
              {
                name: "SCAN_JOB_ID",
                value: events.EventField.fromPath("$.detail.scan_job_id"),
              },
              {
                name: "S3_KEY",
                value: events.EventField.fromPath("$.detail.s3_key"),
              },
              {
                name: "IAC_TYPE",
                value: events.EventField.fromPath("$.detail.iac_type"),
              },
            ],
          },
        ],
      })
    );

    scanRequestedRule.addTarget(
      new targets.EcsTask({
        cluster,
        taskDefinition: checkovTaskDef,
        launchType: ecs.LaunchType.FARGATE,
        assignPublicIp: true,
        subnetSelection: { subnetType: ec2.SubnetType.PUBLIC },
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

    // ─────────────────────────────────────────────────────────────────────────
    // PHASE 9 — Reporting + Notifications (report / email / failure Lambdas)
    // All three share the guardrail-report image; gated by computeEnabled like
    // the other fromEcr Lambdas (image must exist at CreateFunction time).
    // ─────────────────────────────────────────────────────────────────────────
    if (computeEnabled) {
      const cloudFrontUrl = ssm.StringParameter.valueForStringParameter(
        this,
        `/guardrail/${env}/cloudfront-url`
      );

      // Dedicated role — these Lambdas need SES + Secrets, which the scanner
      // ingest/aggregator role deliberately does not have (least privilege).
      const reportingRole = new iam.Role(this, "ReportingLambdaRole", {
        roleName: `guardrail-reporting-lambda-role-${env}`,
        assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
        managedPolicies: [
          iam.ManagedPolicy.fromAwsManagedPolicyName(
            "service-role/AWSLambdaBasicExecutionRole"
          ),
        ],
      });
      props.kmsKey.grantEncryptDecrypt(reportingRole);
      props.scanJobsTable.grantReadWriteData(reportingRole);
      props.findingsTable.grantReadData(reportingRole);
      props.reportsBucket.grantReadWrite(reportingRole);
      props.eventBus.grantPutEventsTo(reportingRole);
      // Grant GetSecretValue on the role itself (referencing the Foundation ARN
      // token) rather than appSecret.grantRead() — the latter mutates the
      // secret's policy in Foundation to name this Scanner role, creating a
      // Foundation→Scanner edge and a dependency cycle. KMS decrypt for the
      // secret is already covered by grantEncryptDecrypt(reportingRole) above.
      reportingRole.addToPolicy(
        new iam.PolicyStatement({
          actions: ["secretsmanager:GetSecretValue"],
          resources: [props.appSecret.secretArn],
        })
      );
      this.reportEcrRepo.grantPull(reportingRole);
      reportingRole.addToPolicy(
        new iam.PolicyStatement({
          actions: ["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
          resources: ["*"],
        })
      );
      // SES scoped to the single verified demo identity (sandbox: From=To).
      reportingRole.addToPolicy(
        new iam.PolicyStatement({
          actions: ["ses:SendRawEmail"],
          resources: [
            `arn:aws:ses:${this.region}:${this.account}:identity/puneetkumarsingh765@gmail.com`,
          ],
        })
      );

      const reportingEnv: Record<string, string> = {
        SCAN_JOBS_TABLE: props.scanJobsTable.tableName,
        FINDINGS_TABLE: props.findingsTable.tableName,
        REPORTS_BUCKET: props.reportsBucket.bucketName,
        EVENT_BUS_NAME: props.eventBus.eventBusName,
        CLOUDFRONT_URL: cloudFrontUrl,
        APP_SECRETS_ARN: props.appSecret.secretArn,
        ENVIRONMENT: env,
        LOG_LEVEL: "INFO",
      };

      const reportImage = (cmd: string) =>
        lambda.DockerImageCode.fromEcr(this.reportEcrRepo, {
          tagOrDigest: `${env}-latest`,
          entrypoint: ["/usr/local/bin/python", "-m", "awslambdaric"],
          cmd: [cmd],
        });

      // ── report-handler: AIAnalysisComplete → PDF in S3 → ReportGenerated ────
      this.reportHandlerFn = new lambda.DockerImageFunction(this, "ReportHandler", {
        functionName: `guardrail-report-handler-${env}`,
        code: reportImage("src.handlers.report_handler.handler"),
        memorySize: 512,
        timeout: cdk.Duration.seconds(120),
        role: reportingRole,
        environment: reportingEnv,
        tracing: lambda.Tracing.ACTIVE,
        logGroup: new logs.LogGroup(this, "ReportHandlerLogs", {
          logGroupName: `/guardrail/${env}/lambda/report-handler`,
          retention: logs.RetentionDays.ONE_WEEK,
          removalPolicy,
        }),
      });

      // ── email-handler: ReportGenerated (success) OR ScanFailed (failure) ────
      this.emailHandlerFn = new lambda.DockerImageFunction(this, "EmailHandler", {
        functionName: `guardrail-email-handler-${env}`,
        code: reportImage("src.handlers.email_handler.handler"),
        memorySize: 256,
        timeout: cdk.Duration.seconds(30),
        role: reportingRole,
        environment: reportingEnv,
        tracing: lambda.Tracing.ACTIVE,
        logGroup: new logs.LogGroup(this, "EmailHandlerLogs", {
          logGroupName: `/guardrail/${env}/lambda/email-handler`,
          retention: logs.RetentionDays.ONE_WEEK,
          removalPolicy,
        }),
      });

      // ── failure-handler: ECS exit≠0 OR DLQ alarm → FAILED → ScanFailed ──────
      this.failureHandlerFn = new lambda.DockerImageFunction(this, "FailureHandler", {
        functionName: `guardrail-failure-handler-${env}`,
        code: reportImage("src.handlers.failure_handler.handler"),
        memorySize: 128,
        timeout: cdk.Duration.seconds(30),
        role: reportingRole,
        environment: reportingEnv,
        tracing: lambda.Tracing.ACTIVE,
        logGroup: new logs.LogGroup(this, "FailureHandlerLogs", {
          logGroupName: `/guardrail/${env}/lambda/failure-handler`,
          retention: logs.RetentionDays.ONE_WEEK,
          removalPolicy,
        }),
      });

      // ── EventBridge rules (custom guardrail bus) ────────────────────────────
      new events.Rule(this, "AiAnalysisCompleteRule", {
        ruleName: `guardrail-ai-analysis-complete-${env}`,
        eventBus: props.eventBus,
        eventPattern: { source: ["guardrail"], detailType: ["AIAnalysisComplete"] },
        targets: [new targets.LambdaFunction(this.reportHandlerFn)],
      });

      new events.Rule(this, "ReportGeneratedRule", {
        ruleName: `guardrail-report-generated-${env}`,
        eventBus: props.eventBus,
        eventPattern: { source: ["guardrail"], detailType: ["ReportGenerated"] },
        targets: [new targets.LambdaFunction(this.emailHandlerFn)],
      });

      new events.Rule(this, "ScanFailedRule", {
        ruleName: `guardrail-scan-failed-${env}`,
        eventBus: props.eventBus,
        eventPattern: { source: ["guardrail"], detailType: ["ScanFailed"] },
        targets: [new targets.LambdaFunction(this.emailHandlerFn)],
      });

      // ECS TaskStopped with a non-zero container exit → failure-handler.
      // Default bus (aws.ecs), scoped to OUR cluster so other tasks don't trip it.
      new events.Rule(this, "EcsTaskFailedRule", {
        ruleName: `guardrail-ecs-task-failed-${env}`,
        eventPattern: {
          source: ["aws.ecs"],
          detailType: ["ECS Task State Change"],
          detail: {
            clusterArn: [cluster.clusterArn],
            lastStatus: ["STOPPED"],
            containers: { exitCode: [{ "anything-but": 0 }] },
          },
        },
        targets: [new targets.LambdaFunction(this.failureHandlerFn)],
      });

      // ── DLQ depth alarm → SNS → failure-handler ─────────────────────────────
      const dlqTopic = new sns.Topic(this, "DlqAlertsTopic", {
        topicName: `guardrail-dlq-alerts-${env}`,
        masterKey: props.kmsKey,
      });
      dlqTopic.applyRemovalPolicy(removalPolicy);
      dlqTopic.addSubscription(
        new snsSubscriptions.LambdaSubscription(this.failureHandlerFn)
      );

      const dlqAlarm = new cloudwatch.Alarm(this, "CheckovDlqDepthAlarm", {
        alarmName: `guardrail-checkov-dlq-depth-${env}`,
        alarmDescription:
          "Checkov results landed in the DLQ — a scan stage is failing.",
        metric: checkovDlq.metricApproximateNumberOfMessagesVisible({
          period: cdk.Duration.minutes(1),
          statistic: "Maximum",
        }),
        threshold: 0,
        evaluationPeriods: 1,
        comparisonOperator:
          cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      });
      dlqAlarm.addAlarmAction(new cloudwatchActions.SnsAction(dlqTopic));
    }

    // ── Tags ──────────────────────────────────────────────────────────────────
    Object.entries(commonTags).forEach(([k, v]) => cdk.Tags.of(this).add(k, v));
  }
}
