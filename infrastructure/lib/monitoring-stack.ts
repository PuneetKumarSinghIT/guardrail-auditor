import * as cdk from "aws-cdk-lib";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as cloudwatchActions from "aws-cdk-lib/aws-cloudwatch-actions";
import * as kms from "aws-cdk-lib/aws-kms";
import * as sns from "aws-cdk-lib/aws-sns";
import * as snsSubscriptions from "aws-cdk-lib/aws-sns-subscriptions";
import * as ssm from "aws-cdk-lib/aws-ssm";
import { Construct } from "constructs";

interface MonitoringStackProps extends cdk.StackProps {
  kmsKey: kms.Key;
}

// ─────────────────────────────────────────────────────────────────────────────
// MONITORING STACK (Phase 9 — observability)
//
//   CloudWatch Dashboard "GuardrailHealth-{env}":
//     - scan throughput (report-handler invocations ≈ completed scans)
//     - Lambda + ECS error rates
//     - AI / Bedrock latency (ai-analyzer Duration p95)
//   Alarms → SNS guardrail-ops-alerts → email:
//     - Lambda errors across the pipeline
//     - Bedrock p95 latency > 10s
//
// IMPORTANT: this stack references the pipeline Lambdas BY METRIC DIMENSION
// (function-name strings), never by construct import. That keeps it decoupled
// from the computeEnabled two-phase gate — a monitoring deploy never pulls the
// scanner/ai stacks into its change set, so it can't strip their Lambdas.
// X-Ray active tracing is set on each Lambda in its own stack (tracing: ACTIVE),
// so there is nothing to enable here for tracing.
// ─────────────────────────────────────────────────────────────────────────────

export class MonitoringStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: MonitoringStackProps) {
    super(scope, id, props);

    const env = this.node.tryGetContext("env") ?? "dev";
    const removalPolicy = cdk.RemovalPolicy.DESTROY;

    const PIPELINE_FUNCTIONS = [
      `guardrail-ingest-handler-${env}`,
      `guardrail-aggregator-${env}`,
      `guardrail-ai-analyzer-${env}`,
      `guardrail-report-handler-${env}`,
      `guardrail-email-handler-${env}`,
      `guardrail-failure-handler-${env}`,
      `guardrail-api-handler-${env}`,
    ];
    const AI_FUNCTION = `guardrail-ai-analyzer-${env}`;
    const REPORT_FUNCTION = `guardrail-report-handler-${env}`;

    const lambdaMetric = (
      fnName: string,
      metricName: string,
      statistic: string
    ): cloudwatch.Metric =>
      new cloudwatch.Metric({
        namespace: "AWS/Lambda",
        metricName,
        statistic,
        period: cdk.Duration.minutes(5),
        dimensionsMap: { FunctionName: fnName },
      });

    // ── Ops alerts topic ──────────────────────────────────────────────────────
    const opsTopic = new sns.Topic(this, "OpsAlertsTopic", {
      topicName: `guardrail-ops-alerts-${env}`,
      masterKey: props.kmsKey,
    });
    opsTopic.applyRemovalPolicy(removalPolicy);
    opsTopic.addSubscription(
      new snsSubscriptions.EmailSubscription("puneetkumarsingh765@gmail.com")
    );

    // ── Dashboard ─────────────────────────────────────────────────────────────
    const dashboard = new cloudwatch.Dashboard(this, "HealthDashboard", {
      dashboardName: `GuardrailHealth-${env}`,
    });

    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: "Scan throughput (report-handler invocations ≈ completed scans)",
        left: [lambdaMetric(REPORT_FUNCTION, "Invocations", "Sum")],
        width: 12,
      }),
      new cloudwatch.GraphWidget({
        title: "Lambda errors (pipeline)",
        left: PIPELINE_FUNCTIONS.map((fn) =>
          lambdaMetric(fn, "Errors", "Sum")
        ),
        width: 12,
      })
    );

    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: "Lambda duration p95",
        left: PIPELINE_FUNCTIONS.map((fn) => lambdaMetric(fn, "Duration", "p95")),
        width: 12,
      }),
      new cloudwatch.GraphWidget({
        title: "AI analyzer (Bedrock) latency p95",
        left: [lambdaMetric(AI_FUNCTION, "Duration", "p95")],
        width: 12,
      })
    );

    // ── Alarms ────────────────────────────────────────────────────────────────
    // One Errors alarm per pipeline function (any error over 5 min pages ops).
    PIPELINE_FUNCTIONS.forEach((fn, i) => {
      const alarm = new cloudwatch.Alarm(this, `LambdaErrorsAlarm${i}`, {
        alarmName: `guardrail-errors-${fn}`,
        alarmDescription: `${fn} reported Lambda errors`,
        metric: lambdaMetric(fn, "Errors", "Sum"),
        threshold: 1,
        evaluationPeriods: 1,
        comparisonOperator:
          cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      });
      alarm.addAlarmAction(new cloudwatchActions.SnsAction(opsTopic));
    });

    // Bedrock p95 latency > 10s (proxy: ai-analyzer Duration, which is dominated
    // by the Bedrock round-trip).
    const aiLatencyAlarm = new cloudwatch.Alarm(this, "AiLatencyAlarm", {
      alarmName: `guardrail-ai-latency-${env}`,
      alarmDescription: "ai-analyzer p95 duration > 10s — Bedrock is slow",
      metric: lambdaMetric(AI_FUNCTION, "Duration", "p95"),
      threshold: 10_000,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    aiLatencyAlarm.addAlarmAction(new cloudwatchActions.SnsAction(opsTopic));

    new ssm.StringParameter(this, "OpsTopicArnParam", {
      parameterName: `/guardrail/${env}/ops-topic-arn`,
      stringValue: opsTopic.topicArn,
    }).applyRemovalPolicy(removalPolicy);

    new ssm.StringParameter(this, "DashboardNameParam", {
      parameterName: `/guardrail/${env}/dashboard-name`,
      stringValue: dashboard.dashboardName,
    }).applyRemovalPolicy(removalPolicy);

    cdk.Tags.of(this).add("Project", "SecurityGuardrailAuditor");
    cdk.Tags.of(this).add("Environment", env);
    cdk.Tags.of(this).add("Owner", "puneet-singh");
    cdk.Tags.of(this).add("CostCenter", "demo-portfolio");
  }
}
