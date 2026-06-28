import * as cdk from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as ecr from "aws-cdk-lib/aws-ecr";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as logs from "aws-cdk-lib/aws-logs";
import * as ssm from "aws-cdk-lib/aws-ssm";
import { Construct } from "constructs";

interface AiStackProps extends cdk.StackProps {
  scanJobsTable: dynamodb.Table;
  findingsTable: dynamodb.Table;
  kmsKey: cdk.aws_kms.Key;
  eventBus: events.EventBus;
}

// ─────────────────────────────────────────────────────────────────────────────
// AI ANALYSIS STACK
//   guardrail-ai-engine-{env}  ← Lambda: ai-analyzer (boto3 + awslambdaric)
//
// Triggered by the ScanComplete event (custom guardrail bus, published by the
// aggregator). For each finding it calls Bedrock Haiku (explain) + Sonnet (fix
// for CRITICAL/HIGH only), writes results back, computes risk_score, flips the
// job to AI_COMPLETE, and publishes AIAnalysisComplete for the report stage.
//
// Same ECR bootstrap deadlock as the scanner stack: DockerImageFunction.fromEcr
// needs its image at CreateFunction time, but this stack also creates the repo.
// The computeEnabled flag gates the Lambda so a fresh deploy is: (A) repos only,
// (B) push image, (C) deploy Lambda. See scripts/deploy_env.sh.
// ─────────────────────────────────────────────────────────────────────────────

export class AiStack extends cdk.Stack {
  public readonly analyzerFn?: lambda.DockerImageFunction;
  public readonly aiEngineEcrRepo: ecr.Repository;

  constructor(scope: Construct, id: string, props: AiStackProps) {
    super(scope, id, props);

    const env = this.node.tryGetContext("env") ?? "dev";
    const removalPolicy = cdk.RemovalPolicy.DESTROY;
    const computeEnabled =
      this.node.tryGetContext("computeEnabled") !== "false";
    // Phase 11: reserved concurrency is $0 but BLOCKED by this account's Lambda
    // concurrency quota of 10 (unverified-account limit) — gated OFF by default,
    // enable with `--context reservedConcurrency=true` once verified. ai-analyzer: 5.
    const reservedConcurrency =
      this.node.tryGetContext("reservedConcurrency") === "true";

    const commonTags = {
      Project: "SecurityGuardrailAuditor",
      Environment: env,
      Owner: "puneet-singh",
      CostCenter: "demo-portfolio",
    };

    // Locked model choices. Claude 4.x on Bedrock is INFERENCE_PROFILE-only
    // (no on-demand direct foundation-model invoke), so the invoke IDs are the
    // us.* cross-region inference profiles. IAM for an inference-profile invoke
    // needs BOTH the profile ARN AND the underlying foundation-model ARNs in
    // every region the profile can route to (us-east-1/2, us-west-2) — hence the
    // region wildcard on the foundation-model ARNs (still scoped to the 2 models,
    // never "*").
    const EXPLAIN_MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"; // Haiku 4.5
    const FIX_MODEL = "us.anthropic.claude-sonnet-4-6"; // Sonnet 4.6
    const EXPLAIN_FM = "anthropic.claude-haiku-4-5-20251001-v1:0";
    const FIX_FM = "anthropic.claude-sonnet-4-6";
    const fmArn = (id: string) => `arn:aws:bedrock:*::foundation-model/${id}`;
    const profileArn = (id: string) =>
      `arn:aws:bedrock:${this.region}:${this.account}:inference-profile/${id}`;

    // ── ECR: ai-analyzer Lambda image ─────────────────────────────────────────
    // Deps: boto3 + awslambdaric. Dockerfile: ai-engine/Dockerfile (ctx ai-engine/)
    this.aiEngineEcrRepo = new ecr.Repository(this, "AiEngineRepo", {
      repositoryName: `guardrail-ai-engine-${env}`,
      encryptionKey: props.kmsKey,
      imageScanOnPush: true,
      removalPolicy,
      emptyOnDelete: true,
      lifecycleRules: [
        { maxImageCount: 10, description: "Keep last 10 tagged images" },
        {
          maxImageAge: cdk.Duration.days(1),
          tagStatus: ecr.TagStatus.UNTAGGED,
          description: "Delete untagged images after 1 day",
        },
      ],
    });

    new ssm.StringParameter(this, "AiEngineEcrUriParam", {
      parameterName: `/guardrail/${env}/ecr-ai-engine-uri`,
      stringValue: this.aiEngineEcrRepo.repositoryUri,
    });

    // ── Lambda execution role ─────────────────────────────────────────────────
    const analyzerRole = new iam.Role(this, "AiAnalyzerRole", {
      roleName: `guardrail-ai-analyzer-role-${env}`,
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          "service-role/AWSLambdaBasicExecutionRole"
        ),
      ],
    });

    props.kmsKey.grantEncryptDecrypt(analyzerRole);
    props.findingsTable.grantReadWriteData(analyzerRole);
    props.scanJobsTable.grantReadWriteData(analyzerRole);
    props.eventBus.grantPutEventsTo(analyzerRole);
    this.aiEngineEcrRepo.grantPull(analyzerRole);

    analyzerRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
        resources: ["*"],
      })
    );

    // anthropic provider: bedrock:InvokeModel scoped to the 2 inference profiles +
    // their backing foundation models (never "*"). Required once model access is granted.
    analyzerRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["bedrock:InvokeModel"],
        resources: [
          profileArn(EXPLAIN_MODEL),
          profileArn(FIX_MODEL),
          fmArn(EXPLAIN_FM),
          fmArn(FIX_FM),
        ],
      })
    );

    // openai_compat provider (works today): the analyzer generates a short-lived bearer
    // token from THIS role's creds (no stored secret) and calls gpt-oss on the OpenAI-
    // compatible endpoint, which runs on the `bedrock-mantle` PREVIEW service. Both the
    // CallWithBearerToken auth and the CreateInference invoke are bedrock-mantle actions
    // (NOT the bedrock namespace) — discovered from the endpoint's own authz errors;
    // admin only worked because it had "*". Granted as bedrock-mantle:* (scoped to the
    // preview service namespace) so additional preview actions don't break it.
    analyzerRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["bedrock-mantle:*"],
        resources: ["*"],
      })
    );

    // ── Lambda + EventBridge wiring (compute pass only) ──────────────────────
    if (computeEnabled) {
      this.analyzerFn = new lambda.DockerImageFunction(this, "AiAnalyzer", {
        functionName: `guardrail-ai-analyzer-${env}`,
        code: lambda.DockerImageCode.fromEcr(this.aiEngineEcrRepo, {
          tagOrDigest: `${env}-latest`,
          entrypoint: ["/usr/local/bin/python", "-m", "awslambdaric"],
          cmd: ["src.analyzer.handler"],
        }),
        memorySize: 512,
        timeout: cdk.Duration.seconds(300),
        role: analyzerRole,
        reservedConcurrentExecutions: reservedConcurrency ? 5 : undefined,
        environment: {
          FINDINGS_TABLE: props.findingsTable.tableName,
          SCAN_JOBS_TABLE: props.scanJobsTable.tableName,
          EVENT_BUS_NAME: props.eventBus.eventBusName,
          // Provider switch: "openai_compat" works today (gpt-oss via runtime-generated
          // bearer token, no stored secret); flip to "anthropic" once Bedrock model
          // access is granted to use Claude Haiku/Sonnet via pure IAM.
          BEDROCK_PROVIDER: "openai_compat",
          BEDROCK_EXPLAIN_MODEL: EXPLAIN_MODEL,
          BEDROCK_FIX_MODEL: FIX_MODEL,
          BEDROCK_OPENAI_EXPLAIN_MODEL: "openai.gpt-oss-120b",
          BEDROCK_OPENAI_FIX_MODEL: "openai.gpt-oss-120b",
          LOG_LEVEL: "INFO",
        },
        tracing: lambda.Tracing.ACTIVE,
        logGroup: new logs.LogGroup(this, "AiAnalyzerLogs", {
          logGroupName: `/guardrail/${env}/lambda/ai-analyzer`,
          retention: logs.RetentionDays.ONE_WEEK,
          removalPolicy,
        }),
      });

      // ScanComplete (custom bus, from aggregator) → ai-analyzer
      new events.Rule(this, "ScanCompleteRule", {
        ruleName: `guardrail-scan-complete-${env}`,
        eventBus: props.eventBus,
        eventPattern: {
          source: ["guardrail"],
          detailType: ["ScanComplete"],
        },
        targets: [new targets.LambdaFunction(this.analyzerFn)],
      });
    }

    Object.entries(commonTags).forEach(([k, v]) => cdk.Tags.of(this).add(k, v));
  }
}
