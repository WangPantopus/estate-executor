"use client";

import { useMemo } from "react";
import { ApiClient } from "@/lib/api-client";

/**
 * Returns a memoized ApiClient instance with auth token injection.
 *
 * In the Auth0 Next.js SDK v4, access tokens are obtained server-side
 * via the middleware/route handler. Client-side requests go through
 * Next.js API routes which attach the token automatically, or you can
 * call getAccessToken() from @auth0/nextjs-auth0 on the server.
 *
 * For client components making direct API calls, we create an ApiClient
 * that fetches a token from the /auth/token endpoint (which proxies
 * the Auth0 SDK's getAccessToken server-side).
 */
export function useApi(): ApiClient {
  return useMemo(
    () =>
      new ApiClient({
        getAccessToken: async () => {
          try {
            const res = await fetch("/auth/token");
            if (!res.ok) return null;
            const { accessToken } = await res.json();
            return accessToken ?? null;
          } catch {
            return null;
          }
        },
      }),
    [],
  );
}
