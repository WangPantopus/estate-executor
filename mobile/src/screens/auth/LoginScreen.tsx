/**
 * Login screen — Auth0 login with luxury branding.
 */

import React, { useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { Button } from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";
import { colors, spacing, fontSize, fontWeight } from "@/lib/theme";

export function LoginScreen() {
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async () => {
    setLoading(true);
    setError(null);
    const success = await login();
    setLoading(false);
    if (!success) {
      setError("Login failed. Please try again.");
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        {/* Logo */}
        <View style={styles.logo}>
          <Text style={styles.logoText}>EE</Text>
        </View>
        <Text style={styles.title}>Estate Executor</Text>
        <Text style={styles.titleAccent}>OS</Text>
      </View>

      <View style={styles.content}>
        <Text style={styles.subtitle}>
          Coordination Operating System{"\n"}for Estate Administration
        </Text>

        {error && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}

        <Button
          title="Sign In"
          variant="primary"
          size="lg"
          onPress={handleLogin}
          loading={loading}
        />

        <Button
          title="Create Account"
          variant="outline"
          size="lg"
          onPress={handleLogin}
          style={styles.signupButton}
        />
      </View>

      <Text style={styles.footer}>
        Secure. Compliant. Professional.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.primary,
    paddingHorizontal: spacing["2xl"],
    justifyContent: "center",
  },
  header: {
    alignItems: "center",
    marginBottom: spacing["4xl"],
  },
  logo: {
    width: 64,
    height: 64,
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.15)",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.lg,
  },
  logoText: {
    fontSize: fontSize["2xl"],
    fontWeight: fontWeight.bold,
    color: colors.white,
  },
  title: {
    fontSize: fontSize["2xl"],
    fontWeight: fontWeight.medium,
    color: colors.white,
    letterSpacing: -0.5,
  },
  titleAccent: {
    fontSize: fontSize["2xl"],
    fontWeight: fontWeight.medium,
    color: colors.gold,
    marginTop: -4,
  },
  content: {
    gap: spacing.lg,
  },
  subtitle: {
    fontSize: fontSize.base,
    color: "rgba(255,255,255,0.6)",
    textAlign: "center",
    lineHeight: 22,
    marginBottom: spacing.lg,
  },
  errorBox: {
    backgroundColor: "rgba(220, 38, 38, 0.15)",
    padding: spacing.md,
    borderRadius: 8,
  },
  errorText: {
    color: "#fca5a5",
    fontSize: fontSize.sm,
    textAlign: "center",
  },
  signupButton: {
    borderColor: "rgba(255,255,255,0.2)",
  },
  footer: {
    fontSize: fontSize.xs,
    color: "rgba(255,255,255,0.3)",
    textAlign: "center",
    marginTop: spacing["4xl"],
    letterSpacing: 1,
    textTransform: "uppercase",
  },
});
