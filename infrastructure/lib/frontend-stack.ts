import * as cdk from "aws-cdk-lib";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as iam from "aws-cdk-lib/aws-iam";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as ssm from "aws-cdk-lib/aws-ssm";
import { Construct } from "constructs";

// No extra props — the dashboard bucket name is deterministic and reconstructed
// locally (see below), so this stack never references a Foundation token/output.
type FrontendStackProps = cdk.StackProps;

// ─────────────────────────────────────────────────────────────────────────────
// FRONTEND STACK
//   guardrail-dashboard-{env}-{account}  ← S3 origin (created in FoundationStack)
//   CloudFront distribution (OAC)        ← HTTPS delivery + SPA routing
//
// Pure S3 + CloudFront — no Lambda, no ECR, so no compute-bootstrap gate.
//
// SPA routing: 403/404 from S3 (a client-side route with no matching object)
// are rewritten to /index.html (200) so React Router can resolve the path.
//
// The 04-deploy-frontend.yml workflow reads these SSM params after deploy:
//   /guardrail/{env}/cloudfront-dist-id  → CloudFront invalidation target
//   /guardrail/{env}/cloudfront-url      → public dashboard URL
// ─────────────────────────────────────────────────────────────────────────────

export class FrontendStack extends cdk.Stack {
  public readonly distribution: cloudfront.Distribution;

  constructor(scope: Construct, id: string, props: FrontendStackProps) {
    super(scope, id, props);

    const env = this.node.tryGetContext("env") ?? "dev";

    cdk.Tags.of(this).add("Project", "SecurityGuardrailAuditor");
    cdk.Tags.of(this).add("Environment", env);
    cdk.Tags.of(this).add("Owner", "puneet-singh");
    cdk.Tags.of(this).add("CostCenter", "demo-portfolio");

    // Reconstruct the deterministic bucket name (created in FoundationStack as
    // `guardrail-dashboard-${env}-${account}`). Using a literal string — NOT a
    // Foundation construct token — keeps this stack free of any cross-stack
    // output reference (a token here caused Fn::GetStackOutput to fail) and
    // avoids the OAC dependency cycle. The Frontend→Foundation deploy ordering
    // is enforced by the explicit addDependency in bin/app.ts.
    const dashboardBucketName = `guardrail-dashboard-${env}-${this.account}`;
    const bucket = s3.Bucket.fromBucketName(
      this,
      "DashboardBucket",
      dashboardBucketName
    );

    // OAC origin. For an imported bucket, withOriginAccessControl creates the OAC
    // and wires the origin, but cannot manage the (foreign) bucket policy — we
    // add it explicitly below.
    const s3Origin = origins.S3BucketOrigin.withOriginAccessControl(bucket);

    this.distribution = new cloudfront.Distribution(this, "Distribution", {
      comment: `Guardrail Auditor dashboard (${env})`,
      defaultRootObject: "index.html",
      priceClass: cloudfront.PriceClass.PRICE_CLASS_100, // NA + EU only — cheapest
      defaultBehavior: {
        origin: s3Origin,
        viewerProtocolPolicy:
          cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
        compress: true,
      },
      // SPA fallback — unknown paths resolve to index.html so React Router
      // (client-side routing) handles /scans, /scans/{id}, etc.
      errorResponses: [
        {
          httpStatus: 403,
          responseHttpStatus: 200,
          responsePagePath: "/index.html",
          ttl: cdk.Duration.minutes(5),
        },
        {
          httpStatus: 404,
          responseHttpStatus: 200,
          responsePagePath: "/index.html",
          ttl: cdk.Duration.minutes(5),
        },
      ],
    });

    // OAC bucket policy — added in THIS stack (not Foundation) to avoid a cycle.
    // Allows only this distribution to read objects via the CloudFront service
    // principal, scoped by the distribution ARN.
    new s3.CfnBucketPolicy(this, "DashboardOacPolicy", {
      bucket: dashboardBucketName,
      policyDocument: new iam.PolicyDocument({
        statements: [
          new iam.PolicyStatement({
            sid: "AllowCloudFrontOacRead",
            effect: iam.Effect.ALLOW,
            principals: [
              new iam.ServicePrincipal("cloudfront.amazonaws.com"),
            ],
            actions: ["s3:GetObject"],
            resources: [`arn:aws:s3:::${dashboardBucketName}/*`],
            conditions: {
              StringEquals: {
                "AWS:SourceArn": `arn:aws:cloudfront::${this.account}:distribution/${this.distribution.distributionId}`,
              },
            },
          }),
        ],
      }),
    });

    const cfUrl = `https://${this.distribution.distributionDomainName}`;

    const distIdParam = new ssm.StringParameter(this, "CloudFrontDistIdParam", {
      parameterName: `/guardrail/${env}/cloudfront-dist-id`,
      stringValue: this.distribution.distributionId,
    });
    distIdParam.applyRemovalPolicy(cdk.RemovalPolicy.DESTROY);

    const cfUrlParam = new ssm.StringParameter(this, "CloudFrontUrlParam", {
      parameterName: `/guardrail/${env}/cloudfront-url`,
      stringValue: cfUrl,
    });
    cfUrlParam.applyRemovalPolicy(cdk.RemovalPolicy.DESTROY);

    new cdk.CfnOutput(this, "DistributionId", {
      value: this.distribution.distributionId,
    });
    new cdk.CfnOutput(this, "CloudFrontUrl", { value: cfUrl });
  }
}
