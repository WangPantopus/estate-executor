/**
 * Auth0 integration for React Native.
 *
 * Uses expo-auth-session for the OAuth flow and expo-secure-store
 * for persisting tokens securely on device.
 */

import * as AuthSession from "expo-auth-session";
import * as SecureStore from "expo-secure-store";
import * as WebBrowser from "expo-web-browser";

// Complete any pending auth session
WebBrowser.maybeCompleteAuthSession();

// ─── Configuration ──────────────────────────────────────────────────────────

const AUTH0_DOMAIN = process.env.EXPO_PUBLIC_AUTH0_DOMAIN ?? "auth.estate-executor.com";
const AUTH0_CLIENT_ID = process.env.EXPO_PUBLIC_AUTH0_CLIENT_ID ?? "";
const AUTH0_AUDIENCE = process.env.EXPO_PUBLIC_AUTH0_AUDIENCE ?? "https://api.estate-executor.com";

const TOKEN_KEY = "auth_access_token";
const REFRESH_TOKEN_KEY = "auth_refresh_token";
const USER_KEY = "auth_user";

const discovery = {
  authorizationEndpoint: `https://${AUTH0_DOMAIN}/authorize`,
  tokenEndpoint: `https://${AUTH0_DOMAIN}/oauth/token`,
  revocationEndpoint: `https://${AUTH0_DOMAIN}/oauth/revoke`,
};

const redirectUri = AuthSession.makeRedirectUri({
  scheme: "estate-executor",
});

// ─── Token storage ──────────────────────────────────────────────────────────

export async function getStoredToken(): Promise<string | null> {
  try {
    return await SecureStore.getItemAsync(TOKEN_KEY);
  } catch {
    return null;
  }
}

export async function setStoredToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(TOKEN_KEY, token);
}

export async function clearStoredTokens(): Promise<void> {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
  await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
  await SecureStore.deleteItemAsync(USER_KEY);
}

// ─── Auth0 login flow ───────────────────────────────────────────────────────

export interface AuthResult {
  accessToken: string;
  expiresIn?: number;
}

export async function loginWithAuth0(): Promise<AuthResult | null> {
  const request = new AuthSession.AuthRequest({
    clientId: AUTH0_CLIENT_ID,
    redirectUri,
    scopes: ["openid", "profile", "email", "offline_access"],
    responseType: AuthSession.ResponseType.Code,
    usePKCE: true,
    extraParams: {
      audience: AUTH0_AUDIENCE,
    },
  });

  const result = await request.promptAsync(discovery);

  if (result.type !== "success" || !result.params["code"]) {
    return null;
  }

  // Exchange code for tokens
  const tokenResult = await AuthSession.exchangeCodeAsync(
    {
      clientId: AUTH0_CLIENT_ID,
      code: result.params["code"],
      redirectUri,
      extraParams: {
        code_verifier: request.codeVerifier ?? "",
      },
    },
    discovery,
  );

  if (tokenResult.accessToken) {
    await setStoredToken(tokenResult.accessToken);
    if (tokenResult.refreshToken) {
      await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, tokenResult.refreshToken);
    }
    return {
      accessToken: tokenResult.accessToken,
      expiresIn: tokenResult.expiresIn ?? undefined,
    };
  }

  return null;
}

// ─── Logout ─────────────────────────────────────────────────────────────────

export async function logout(): Promise<void> {
  await clearStoredTokens();
  // Optionally open Auth0 logout endpoint to clear server session
  const logoutUrl = `https://${AUTH0_DOMAIN}/v2/logout?client_id=${AUTH0_CLIENT_ID}&returnTo=${encodeURIComponent(redirectUri)}`;
  await WebBrowser.openBrowserAsync(logoutUrl);
}
