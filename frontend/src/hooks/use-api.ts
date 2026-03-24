"use client";

import { useMemo } from "react";
import { ApiClient } from "@/lib/api-client";

/**
 * Cached access token to avoid fetching from /auth/token on every API call.
 * Token is cached for 4 minutes (tokens typically expire in 5-15 min).
 */
let _cachedToken: string | null = null;
let _tokenExpiresAt = 0;
const TOKEN_CACHE_MS = 4 * 60 * 1000; // 4 minutes

async function getCachedAccessToken(): Promise<string | null> {
  const now = Date.now();
  if (_cachedToken && now < _tokenExpiresAt) {
    return _cachedToken;
  }

  try {
    const res = await fetch("/auth/token");
    if (!res.ok) {
      _cachedToken = null;
      return null;
    }
    const { accessToken } = await res.json();
    _cachedToken = accessToken ?? null;
    _tokenExpiresAt = now + TOKEN_CACHE_MS;
    return _cachedToken;
  } catch {
    _cachedToken = null;
    return null;
  }
}

/**
 * Returns a memoized ApiClient instance with cached auth token injection.
 *
 * The token is cached for 4 minutes to eliminate per-request round-trips
 * to /auth/token. On expiry, the next API call transparently refreshes it.
 */
export function useApi(): ApiClient {
  return useMemo(
    () =>
      new ApiClient({
        getAccessToken: getCachedAccessToken,
      }),
    [],
  );
}

/**
 * Invalidate the cached token (e.g., on logout or 401 response).
 */
export function invalidateTokenCache(): void {
  _cachedToken = null;
  _tokenExpiresAt = 0;
}
