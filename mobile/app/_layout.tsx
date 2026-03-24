/**
 * Root layout — wraps the entire app with providers.
 */

import React from "react";
import { StatusBar } from "expo-status-bar";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Stack } from "expo-router";
import { AuthProvider } from "@/hooks/useAuth";
import { NotificationProvider } from "@/hooks/useNotifications";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 2,
      // Keep data in cache for offline reading (24 hours)
      gcTime: 24 * 60 * 60 * 1000,
    },
  },
});

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <NotificationProvider>
          <StatusBar style="auto" />
          <Stack screenOptions={{ headerShown: false }}>
            <Stack.Screen name="(tabs)" />
            <Stack.Screen name="auth" />
          </Stack>
        </NotificationProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
