/**
 * Auth0 integration helpers.
 * TODO: Implement Auth0 SDK integration in Prompt 002.
 */

export function getAuthUrl(): string {
  return process.env.NEXT_PUBLIC_AUTH0_DOMAIN || "";
}

export function getClientId(): string {
  return process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID || "";
}
