import * as cdk from "aws-cdk-lib";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as cognito from "aws-cdk-lib/aws-cognito";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as ecr from "aws-cdk-lib/aws-ecr";
import * as iam from "aws-cdk-lib/aws-iam";
import * as kms from "aws-cdk-lib/aws-kms";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as logs from "aws-cdk-lib/aws-logs";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as ssm from "aws-cdk-lib/aws-ssm";
import { Construct } from "constructs";

interface ApiStackProps extends cdk.StackProps {
  scanJobsTable: dynamodb.Table;
  findingsTable: dynamodb.Table;
  rulesCatalogTable: dynamodb.Table;
  uploadsBucket: s3.Bucket;
  reportsBucket: s3.Bucket;
  kmsKey: kms.Key;
  userPool: cognito.UserPool;
  userPoolClient: cognito.UserPoolClient;
}

// ─────────────────────────────────────────────────────────────────────────────
// API STACK
//   guardrail-api-{env}  ← Lambda: api-handler (boto3 + awslambdaric + python-jose)
//
// One Lambda behind an API Gateway REST API with a Cognito User Pool authorizer.
// Routes (all JWT-protected):
//   POST /v1/scans                      -> presigned upload URL + scan_job_id
//   GET  /v1/scans                      -> list scans
//   GET  /v1/scans/{scan_job_id}        -> detail + findings
//   GET  /v1/scans/{scan_job_id}/report -> presigned PDF URL
//
// Same ECR bootstrap deadlock as the scanner/ai stacks: DockerImageFunction.fromEcr
// needs its image at CreateFunction time, but this stack also creates the repo.
// The computeEnabled flag gates the Lambda + API Gateway so a fresh deploy is:
// (A) repo only, (B) push image, (C) deploy Lambda + API. See scripts/deploy_env.sh.
// ─────────────────────────────────────────────────────────────────────────────

export class ApiStack extends cdk.Stack {
  public readonly apiEcrRepo: ecr.Repository;
  public readonly apiFn?: lambda.DockerImageFunction;

  constructor(scope: Construct, id: string, props: ApiStackProps) {
    super(scope, id, props);

    const env = this.node.tryGetContext("env") ?? "dev";
    const removalPolicy = cdk.RemovalPolicy.DESTROY;
    const computeEnabled =
      this.node.tryGetContext("computeEnabled") !== "false";
    // Phase 11: reserved concurrency is $0 but BLOCKED by this account's Lambda
    // concurrency quota of 10 (unverified-account limit) — gated OFF by default,
    // enable with `--context reservedConcurrency=true` once the account is
    // verified. See CLAUDE.md Phase 11 note. api-handler target: 20.
    const reservedConcurrency =
      this.node.tryGetContext("reservedConcurrency") === "true";
    // CloudFront URL is only known in Phase 8 — until then "*" lets the local
    // Vite dev server call the API. Override via --context corsOrigin=https://...
    const corsOrigin = this.node.tryGetContext("corsOrigin") ?? "*";

    const commonTags = {
      Project: "SecurityGuardrailAuditor",
      Environment: env,
      Owner: "puneet-singh",
      CostCenter: "demo-portfolio",
    };

    // ── ECR: api-handler Lambda image ────────────────────────────────────────
    this.apiEcrRepo = new ecr.Repository(this, "ApiRepo", {
      repositoryName: `guardrail-api-${env}`,
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

    new ssm.StringParameter(this, "ApiEcrUriParam", {
      parameterName: `/guardrail/${env}/ecr-api-uri`,
      stringValue: this.apiEcrRepo.repositoryUri,
    });

    // ── Lambda execution role ────────────────────────────────────────────────
    const apiRole = new iam.Role(this, "ApiHandlerRole", {
      roleName: `guardrail-api-role-${env}`,
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          "service-role/AWSLambdaBasicExecutionRole"
        ),
      ],
    });

    props.kmsKey.grantEncryptDecrypt(apiRole);
    props.scanJobsTable.grantReadWriteData(apiRole); // POST creates QUEUED record
    props.findingsTable.grantReadData(apiRole);
    props.rulesCatalogTable.grantReadData(apiRole);
    props.uploadsBucket.grantPut(apiRole); // presigned PUT inherits role perms
    props.reportsBucket.grantRead(apiRole); // presigned GET for PDF
    this.apiEcrRepo.grantPull(apiRole);

    apiRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
        resources: ["*"],
      })
    );

    // ── Lambda + API Gateway (compute pass only) ─────────────────────────────
    if (computeEnabled) {
      this.apiFn = new lambda.DockerImageFunction(this, "ApiHandler", {
        functionName: `guardrail-api-${env}`,
        code: lambda.DockerImageCode.fromEcr(this.apiEcrRepo, {
          tagOrDigest: `${env}-latest`,
          entrypoint: ["/usr/local/bin/python", "-m", "awslambdaric"],
          cmd: ["src.app.handler"],
        }),
        memorySize: 256,
        timeout: cdk.Duration.seconds(29),
        role: apiRole,
        reservedConcurrentExecutions: reservedConcurrency ? 20 : undefined,
        environment: {
          SCAN_JOBS_TABLE: props.scanJobsTable.tableName,
          FINDINGS_TABLE: props.findingsTable.tableName,
          RULES_TABLE: props.rulesCatalogTable.tableName,
          UPLOAD_BUCKET: props.uploadsBucket.bucketName,
          REPORTS_BUCKET: props.reportsBucket.bucketName,
          COGNITO_USER_POOL_ID: props.userPool.userPoolId,
          COGNITO_CLIENT_ID: props.userPoolClient.userPoolClientId,
          COGNITO_REGION: this.region,
          CORS_ORIGIN: corsOrigin,
          LOG_LEVEL: "INFO",
        },
        tracing: lambda.Tracing.ACTIVE,
        logGroup: new logs.LogGroup(this, "ApiHandlerLogs", {
          logGroupName: `/guardrail/${env}/lambda/api-handler`,
          retention: logs.RetentionDays.ONE_WEEK,
          removalPolicy,
        }),
      });

      const api = new apigateway.RestApi(this, "RestApi", {
        restApiName: `guardrail-api-${env}`,
        description: `Guardrail Auditor REST API (${env})`,
        deployOptions: {
          stageName: env,
          tracingEnabled: true,
          // Phase 11: stage-level throttling (free) — 500 req/s steady, 1000 burst.
          throttlingBurstLimit: 1000,
          throttlingRateLimit: 500,
        },
        defaultCorsPreflightOptions: {
          allowOrigins:
            corsOrigin === "*" ? apigateway.Cors.ALL_ORIGINS : [corsOrigin],
          allowMethods: ["GET", "POST", "OPTIONS"],
          allowHeaders: ["Content-Type", "Authorization"],
        },
      });

      const authorizer = new apigateway.CognitoUserPoolsAuthorizer(
        this,
        "CognitoAuthorizer",
        {
          authorizerName: `guardrail-authorizer-${env}`,
          cognitoUserPools: [props.userPool],
        }
      );

      const integration = new apigateway.LambdaIntegration(this.apiFn, {
        proxy: true,
      });
      const authOpts: apigateway.MethodOptions = {
        authorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
      };

      const v1 = api.root.addResource("v1");
      const scans = v1.addResource("scans");
      scans.addMethod("GET", integration, authOpts);
      scans.addMethod("POST", integration, authOpts);

      const scanById = scans.addResource("{scan_job_id}");
      scanById.addMethod("GET", integration, authOpts);

      const report = scanById.addResource("report");
      report.addMethod("GET", integration, authOpts);

      new ssm.StringParameter(this, "ApiUrlParam", {
        parameterName: `/guardrail/${env}/api-url`,
        stringValue: api.url,
      });
      new cdk.CfnOutput(this, "ApiUrl", { value: api.url });
    }

    Object.entries(commonTags).forEach(([k, v]) => cdk.Tags.of(this).add(k, v));
  }
}
