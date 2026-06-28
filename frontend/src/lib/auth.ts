// Amplify v6 wrapper — thin functions over aws-amplify/auth so the rest of the
// app never imports Amplify directly.

import { Amplify } from "aws-amplify";
import {
  signIn as amplifySignIn,
  signOut as amplifySignOut,
  fetchAuthSession,
  getCurrentUser as amplifyGetCurrentUser,
} from "aws-amplify/auth";
import { env } from "./env";

export function configureAuth(): void {
  // User Pool only — the app talks to the REST API with the Cognito ID token
  // (validated by the API Gateway authorizer). It never touches AWS resources
  // directly from the browser, so no Identity Pool / federated creds are needed.
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId: env.cognitoUserPoolId,
        userPoolClientId: env.cognitoClientId,
      },
    },
  });
}

export async function signIn(email: string, password: string): Promise<void> {
  // USER_PASSWORD_AUTH is enabled on the app client (auth-stack.ts).
  await amplifySignIn({
    username: email,
    password,
    options: { authFlowType: "USER_PASSWORD_AUTH" },
  });
}

export async function signOut(): Promise<void> {
  await amplifySignOut();
}

export async function getCurrentUser() {
  return amplifyGetCurrentUser();
}

// Returns the raw Cognito ID token (JWT) for the Authorization header, or null
// if there is no active session.
export async function getIdToken(): Promise<string | null> {
  try {
    const session = await fetchAuthSession();
    return session.tokens?.idToken?.toString() ?? null;
  } catch {
    return null;
  }
}

export async function isAuthenticated(): Promise<boolean> {
  return (await getIdToken()) !== null;
}
