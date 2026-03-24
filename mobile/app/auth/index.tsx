/**
 * Auth route — shows login screen.
 */

import React from "react";
import { Redirect } from "expo-router";
import { LoginScreen } from "@/screens/auth/LoginScreen";
import { useAuth } from "@/hooks/useAuth";

export default function AuthScreen() {
  const { isAuthenticated } = useAuth();

  if (isAuthenticated) {
    return <Redirect href="/(tabs)" />;
  }

  return <LoginScreen />;
}
