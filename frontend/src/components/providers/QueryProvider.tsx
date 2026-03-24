"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError } from "@/lib/api-client";

/**
 * Query cache timing strategy:
 *
 * - staleTime (5 min): how long data is considered fresh. During this window,
 *   React Query serves from cache without refetching. Estate data (tasks, assets,
 *   documents) doesn't change every 30 seconds — 5 minutes is appropriate.
 *
 * - gcTime (30 min): how long inactive query data stays in memory. Keeps data
 *   available for instant back-navigation without re-fetching.
 *
 * - refetchOnWindowFocus: disabled. Estate admins frequently switch between
 *   browser tabs. Refetching on every focus wastes bandwidth and causes UI
 *   flicker. Real-time updates come via WebSocket instead.
 *
 * - refetchOnReconnect: enabled. If the user was offline, refetch on reconnect
 *   to ensure data is current.
 */
function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000, // 5 minutes
        gcTime: 30 * 60 * 1000, // 30 minutes
        refetchOnWindowFocus: false,
        refetchOnReconnect: true,
        retry: (failureCount, error) => {
          // Don't retry on auth or not-found errors
          if (
            error instanceof ApiError &&
            [401, 403, 404].includes(error.status)
          ) {
            return false;
          }
          return failureCount < 2;
        },
      },
      mutations: {
        retry: false,
      },
    },
  });
}

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(makeQueryClient);

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
