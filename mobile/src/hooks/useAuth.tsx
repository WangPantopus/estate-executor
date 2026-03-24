/**
 * Auth context and hook for the mobile app.
 *
 * Provides authentication state, login, logout, and the API client
 * pre-configured with the user's access token.
 */

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { ApiClient } from "@/lib/api-client";
import { API_BASE_URL } from "@/lib/constants";
import {
  getStoredToken,
  loginWithAuth0,
  logout as auth0Logout,
  clearStoredTokens,
} from "@/lib/auth";
import type { UserProfile } from "@/lib/types";

interface AuthState {
  isLoading: boolean;
  isAuthenticated: boolean;
  user: UserProfile | null;
  accessToken: string | null;
}

interface AuthContextValue extends AuthState {
  login: () => Promise<boolean>;
  logout: () => Promise<void>;
  api: ApiClient;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    isLoading: true,
    isAuthenticated: false,
    user: null,
    accessToken: null,
  });

  const api = useMemo(
    () =>
      new ApiClient({
        baseUrl: API_BASE_URL,
        getAccessToken: async () => state.accessToken,
      }),
    [state.accessToken],
  );

  // Check for stored token on mount
  useEffect(() => {
    let cancelled = false;
    async function restore() {
      const token = await getStoredToken();
      if (cancelled) return;

      if (token) {
        try {
          const tempApi = new ApiClient({
            baseUrl: API_BASE_URL,
            getAccessToken: async () => token,
          });
          const user = await tempApi.getMe();
          if (!cancelled) {
            setState({
              isLoading: false,
              isAuthenticated: true,
              user,
              accessToken: token,
            });
          }
          return;
        } catch {
          await clearStoredTokens();
        }
      }

      if (!cancelled) {
        setState({
          isLoading: false,
          isAuthenticated: false,
          user: null,
          accessToken: null,
        });
      }
    }
    restore();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (): Promise<boolean> => {
    try {
      const result = await loginWithAuth0();
      if (!result) return false;

      const tempApi = new ApiClient({
        baseUrl: API_BASE_URL,
        getAccessToken: async () => result.accessToken,
      });
      const user = await tempApi.getMe();

      setState({
        isLoading: false,
        isAuthenticated: true,
        user,
        accessToken: result.accessToken,
      });
      return true;
    } catch {
      return false;
    }
  }, []);

  const logout = useCallback(async () => {
    await auth0Logout();
    setState({
      isLoading: false,
      isAuthenticated: false,
      user: null,
      accessToken: null,
    });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ ...state, login, logout, api }),
    [state, login, logout, api],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
