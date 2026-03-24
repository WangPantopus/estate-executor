/**
 * Root index — redirects to tabs or auth based on auth state.
 */

import React from "react";
import { Redirect } from "expo-router";
import { useAuth } from "@/hooks/useAuth";
import { LoadingScreen } from "@/components/ui";

export default function Index() {
  const { isLoading, isAuthenticated } = useAuth();

  if (isLoading) {
    return <LoadingScreen />;
  }

  if (isAuthenticated) {
    return <Redirect href="/(tabs)" />;
  }

  return <Redirect href="/auth" />;
}
