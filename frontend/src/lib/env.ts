// Typed access to VITE_* build-time environment variables.
// Values are injected by the 04-deploy-frontend.yml workflow from SSM
// (/guardrail/{env}/*). No VITE_WS_URL — WebSocket is out of scope.

function required(key: keyof ImportMetaEnv): string {
  const value = import.meta.env[key];
  if (!value) {
    // Surfaces a clear console error if a build was made without SSM values.
    console.error(`Missing required environment variable: ${key}`);
  }
  return value ?? "";
}

export const env = {
  apiUrl: required("VITE_API_URL"),
  cognitoUserPoolId: required("VITE_COGNITO_USER_POOL_ID"),
  cognitoClientId: required("VITE_COGNITO_CLIENT_ID"),
  cognitoIdentityPoolId: import.meta.env.VITE_COGNITO_IDENTITY_POOL_ID ?? "",
  region: import.meta.env.VITE_REGION ?? "us-east-1",
} as const;
