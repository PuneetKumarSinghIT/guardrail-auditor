import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as ssm from 'aws-cdk-lib/aws-ssm';

interface AuthStackProps extends cdk.StackProps {
  encryptionKey: kms.Key;
}

export class AuthStack extends cdk.Stack {
  public readonly userPool: cognito.UserPool;
  public readonly userPoolClient: cognito.UserPoolClient;
  public readonly identityPool: cognito.CfnIdentityPool;

  constructor(scope: Construct, id: string, props: AuthStackProps) {
    super(scope, id, props);

    const env = this.node.tryGetContext('env') ?? 'dev';
    const removalPolicy = env === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY;

    cdk.Tags.of(this).add('Project', 'SecurityGuardrailAuditor');
    cdk.Tags.of(this).add('Environment', env);
    cdk.Tags.of(this).add('Owner', 'puneet-singh');
    cdk.Tags.of(this).add('CostCenter', 'demo-portfolio');

    // ── Cognito User Pool ────────────────────────────────────────────
    // selfSignUpEnabled: false — admin creates demo accounts, prevents random signups
    this.userPool = new cognito.UserPool(this, 'UserPool', {
      userPoolName: `guardrail-users-${env}`,
      selfSignUpEnabled: false,
      signInAliases: { email: true },
      autoVerify: { email: true },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: false,
        tempPasswordValidity: cdk.Duration.days(7),
      },
      standardAttributes: {
        email: { required: true, mutable: true },
        fullname: { required: false, mutable: true },
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      removalPolicy,
    });

    // ── App Client — SPA type, no secret ────────────────────────────
    this.userPoolClient = this.userPool.addClient('WebClient', {
      userPoolClientName: `guardrail-web-client-${env}`,
      generateSecret: false,
      authFlows: {
        userPassword: true,
        userSrp: true,
      },
      oAuth: {
        flows: {
          authorizationCodeGrant: true,
        },
        scopes: [
          cognito.OAuthScope.EMAIL,
          cognito.OAuthScope.OPENID,
          cognito.OAuthScope.PROFILE,
        ],
        // localhost for local dev; CloudFront URL updated after Phase 8 deploy
        callbackUrls: ['http://localhost:5173/callback', 'https://placeholder.cloudfront.net/callback'],
        logoutUrls: ['http://localhost:5173', 'https://placeholder.cloudfront.net'],
      },
      accessTokenValidity: cdk.Duration.hours(1),
      idTokenValidity: cdk.Duration.hours(1),
      refreshTokenValidity: cdk.Duration.days(30),
      preventUserExistenceErrors: true,
    });

    // ── Identity Pool ────────────────────────────────────────────────
    // Allows authenticated Cognito users to assume IAM roles for AWS SDK calls
    this.identityPool = new cognito.CfnIdentityPool(this, 'IdentityPool', {
      identityPoolName: `guardrail_identity_${env}`,
      allowUnauthenticatedIdentities: false,
      cognitoIdentityProviders: [{
        clientId: this.userPoolClient.userPoolClientId,
        providerName: this.userPool.userPoolProviderName,
        serverSideTokenCheck: true,
      }],
    });

    // ── SSM Parameters ───────────────────────────────────────────────
    new ssm.StringParameter(this, 'UserPoolIdParam', {
      parameterName: `/guardrail/${env}/cognito-user-pool-id`,
      stringValue: this.userPool.userPoolId,
    });

    new ssm.StringParameter(this, 'ClientIdParam', {
      parameterName: `/guardrail/${env}/cognito-client-id`,
      stringValue: this.userPoolClient.userPoolClientId,
    });

    new ssm.StringParameter(this, 'IdentityPoolIdParam', {
      parameterName: `/guardrail/${env}/cognito-identity-pool-id`,
      stringValue: this.identityPool.ref,
    });

    new ssm.StringParameter(this, 'UserPoolProviderUrlParam', {
      parameterName: `/guardrail/${env}/cognito-user-pool-provider-url`,
      stringValue: this.userPool.userPoolProviderUrl,
    });

    // ── Stack Outputs ────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'UserPoolId', { value: this.userPool.userPoolId });
    new cdk.CfnOutput(this, 'UserPoolClientId', { value: this.userPoolClient.userPoolClientId });
    new cdk.CfnOutput(this, 'IdentityPoolId', { value: this.identityPool.ref });
    new cdk.CfnOutput(this, 'UserPoolProviderUrl', { value: this.userPool.userPoolProviderUrl });
  }
}
