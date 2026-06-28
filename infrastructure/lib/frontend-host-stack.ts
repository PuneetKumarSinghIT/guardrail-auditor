import * as cdk from "aws-cdk-lib";
import * as ecr from "aws-cdk-lib/aws-ecr";
import * as iam from "aws-cdk-lib/aws-iam";
import * as kms from "aws-cdk-lib/aws-kms";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as logs from "aws-cdk-lib/aws-logs";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as ssm from "aws-cdk-lib/aws-ssm";
import { Construct } from "constructs";

interface FrontendHostStackProps extends cdk.StackProps {
  kmsKey: kms.Key;
}

// ─────────────────────────────────────────────────────────────────────────────
// FRONTEND HOST STACK  (stopgap delivery while CloudFront is account-blocked)
//   guardrail-frontend-host-{env}  ← Lambda: serves the SPA bundle from the
//                                    dashboard S3 bucket behind a public
//                                    Function URL (HTTPS, $0 idle).
//
// Same ECR bootstrap deadlock + computeEnabled two-phase gate as scanner/ai/api.
// Reads the SAME dist/ the 04-deploy-frontend.yml workflow syncs to the
// dashboard bucket, so when CloudFront is unblocked nothing has to be rebuilt —
// just deploy GuardrailFrontend-{env} and switch the dashboard URL.
//
// SSM after deploy:  /guardrail/{env}/frontend-url  → public Function URL
// ─────────────────────────────────────────────────────────────────────────────

export class FrontendHostStack extends cdk.Stack {
  public readonly hostEcrRepo: ecr.Repository;
  public readonly hostFn?: lambda.DockerImageFunction;

  constructor(scope: Construct, id: string, props: FrontendHostStackProps) {
    super(scope, id, props);

    const env = this.node.tryGetContext("env") ?? "dev";
    const removalPolicy = cdk.RemovalPolicy.DESTROY;
    const computeEnabled =
      this.node.tryGetContext("computeEnabled") !== "false";

    cdk.Tags.of(this).add("Project", "SecurityGuardrailAuditor");
    cdk.Tags.of(this).add("Environment", env);
    cdk.Tags.of(this).add("Owner", "puneet-singh");
    cdk.Tags.of(this).add("CostCenter", "demo-portfolio");

    // Deterministic dashboard bucket name (created in FoundationStack). Literal
    // string, not a Foundation token → no cross-stack output reference.
    const dashboardBucketName = `guardrail-dashboard-${env}-${this.account}`;

    // ── ECR: frontend-host Lambda image ──────────────────────────────────────
    this.hostEcrRepo = new ecr.Repository(this, "FrontendHostRepo", {
      repositoryName: `guardrail-frontend-host-${env}`,
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

    new ssm.StringParameter(this, "FrontendHostEcrUriParam", {
      parameterName: `/guardrail/${env}/ecr-frontend-host-uri`,
      stringValue: this.hostEcrRepo.repositoryUri,
    });

    // ── Lambda execution role ────────────────────────────────────────────────
    const role = new iam.Role(this, "FrontendHostRole", {
      roleName: `guardrail-frontend-host-role-${env}`,
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          "service-role/AWSLambdaBasicExecutionRole"
        ),
      ],
    });

    props.kmsKey.grantEncryptDecrypt(role); // ECR image layers
    this.hostEcrRepo.grantPull(role);

    // Read-only on the dashboard bucket (imported by name → literal ARN, no ref).
    const dashboardBucket = s3.Bucket.fromBucketName(
      this,
      "DashboardBucket",
      dashboardBucketName
    );
    dashboardBucket.grantRead(role);

    // ── Lambda + Function URL (compute pass only) ────────────────────────────
    if (computeEnabled) {
      this.hostFn = new lambda.DockerImageFunction(this, "FrontendHost", {
        functionName: `guardrail-frontend-host-${env}`,
        code: lambda.DockerImageCode.fromEcr(this.hostEcrRepo, {
          tagOrDigest: `${env}-latest`,
          entrypoint: ["/usr/local/bin/python", "-m", "awslambdaric"],
          cmd: ["src.handler.handler"],
        }),
        memorySize: 256,
        timeout: cdk.Duration.seconds(30),
        role,
        environment: {
          DASHBOARD_BUCKET: dashboardBucketName,
          LOG_LEVEL: "INFO",
        },
        tracing: lambda.Tracing.ACTIVE,
        logGroup: new logs.LogGroup(this, "FrontendHostLogs", {
          logGroupName: `/guardrail/${env}/lambda/frontend-host`,
          retention: logs.RetentionDays.ONE_WEEK,
          removalPolicy,
        }),
      });

      // Public Function URL — the dashboard is a login page; auth is enforced
      // client-side (Cognito) and by the API (JWT). NONE auth lets the browser
      // load the static shell directly.
      const fnUrl = this.hostFn.addFunctionUrl({
        authType: lambda.FunctionUrlAuthType.NONE,
        cors: {
          allowedOrigins: ["*"],
          allowedMethods: [lambda.HttpMethod.GET],
        },
      });

      const urlParam = new ssm.StringParameter(this, "FrontendUrlParam", {
        parameterName: `/guardrail/${env}/frontend-url`,
        stringValue: fnUrl.url,
      });
      urlParam.applyRemovalPolicy(removalPolicy);

      new cdk.CfnOutput(this, "FrontendUrl", { value: fnUrl.url });
    }
  }
}
