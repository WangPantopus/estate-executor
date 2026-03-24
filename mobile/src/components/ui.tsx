/**
 * Reusable UI primitives for the mobile app.
 * Luxury palette with generous spacing and premium feel.
 */

import React from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
  type ViewStyle,
  type TextStyle,
  type PressableProps,
} from "react-native";
import { colors, spacing, fontSize, fontWeight, borderRadius, shadow } from "@/lib/theme";

// ─── Card ───────────────────────────────────────────────────────────────────

interface CardProps {
  children: React.ReactNode;
  style?: ViewStyle;
}

export function Card({ children, style }: CardProps) {
  return <View style={[styles.card, style]}>{children}</View>;
}

// ─── Button ─────────────────────────────────────────────────────────────────

interface ButtonProps extends PressableProps {
  title: string;
  variant?: "primary" | "outline" | "ghost";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  icon?: React.ReactNode;
}

export function Button({
  title,
  variant = "primary",
  size = "md",
  loading = false,
  icon,
  disabled,
  ...rest
}: ButtonProps) {
  const buttonStyle = [
    styles.button,
    variant === "primary" && styles.buttonPrimary,
    variant === "outline" && styles.buttonOutline,
    variant === "ghost" && styles.buttonGhost,
    size === "sm" && styles.buttonSm,
    size === "lg" && styles.buttonLg,
    disabled && styles.buttonDisabled,
  ];

  const textStyle = [
    styles.buttonText,
    variant === "primary" && styles.buttonTextPrimary,
    variant === "outline" && styles.buttonTextOutline,
    variant === "ghost" && styles.buttonTextGhost,
    size === "sm" && styles.buttonTextSm,
  ];

  return (
    <Pressable
      style={({ pressed }) => [
        ...buttonStyle,
        pressed && { opacity: 0.85 },
      ]}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? (
        <ActivityIndicator
          size="small"
          color={variant === "primary" ? colors.white : colors.primary}
        />
      ) : (
        <View style={styles.buttonContent}>
          {icon}
          <Text style={textStyle}>{title}</Text>
        </View>
      )}
    </Pressable>
  );
}

// ─── Badge ──────────────────────────────────────────────────────────────────

interface BadgeProps {
  label: string;
  color?: "green" | "amber" | "red" | "blue" | "gray";
}

const BADGE_COLORS = {
  green: { bg: colors.successLight, text: colors.success },
  amber: { bg: colors.warningLight, text: colors.warning },
  red: { bg: colors.dangerLight, text: colors.danger },
  blue: { bg: colors.infoLight, text: colors.info },
  gray: { bg: colors.muted, text: colors.foregroundMuted },
};

export function Badge({ label, color = "gray" }: BadgeProps) {
  const c = BADGE_COLORS[color];
  return (
    <View style={[styles.badge, { backgroundColor: c.bg }]}>
      <Text style={[styles.badgeText, { color: c.text }]}>{label}</Text>
    </View>
  );
}

// ─── EmptyState ─────────────────────────────────────────────────────────────

interface EmptyStateProps {
  title: string;
  message?: string;
  action?: React.ReactNode;
}

export function EmptyState({ title, message, action }: EmptyStateProps) {
  return (
    <View style={styles.emptyState}>
      <Text style={styles.emptyTitle}>{title}</Text>
      {message && <Text style={styles.emptyMessage}>{message}</Text>}
      {action && <View style={styles.emptyAction}>{action}</View>}
    </View>
  );
}

// ─── LoadingScreen ──────────────────────────────────────────────────────────

export function LoadingScreen() {
  return (
    <View style={styles.loadingScreen}>
      <ActivityIndicator size="large" color={colors.primary} />
    </View>
  );
}

// ─── Divider ────────────────────────────────────────────────────────────────

export function Divider() {
  return <View style={styles.divider} />;
}

// ─── Section Header ─────────────────────────────────────────────────────────

export function SectionHeader({ title }: { title: string }) {
  return (
    <View style={styles.sectionHeader}>
      <Text style={styles.sectionHeaderText}>{title}</Text>
    </View>
  );
}

// ─── Styles ─────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  // Card
  card: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    ...shadow.sm,
  },

  // Button
  button: {
    borderRadius: borderRadius.md,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.xl,
    alignItems: "center",
    justifyContent: "center",
    minHeight: 44,
  },
  buttonPrimary: {
    backgroundColor: colors.primary,
  },
  buttonOutline: {
    backgroundColor: colors.transparent,
    borderWidth: 1,
    borderColor: colors.border,
  },
  buttonGhost: {
    backgroundColor: colors.transparent,
  },
  buttonSm: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    minHeight: 36,
  },
  buttonLg: {
    paddingVertical: spacing.lg,
    paddingHorizontal: spacing["2xl"],
    minHeight: 52,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonContent: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  buttonText: {
    fontSize: fontSize.base,
    fontWeight: fontWeight.medium,
  },
  buttonTextPrimary: {
    color: colors.white,
  },
  buttonTextOutline: {
    color: colors.foreground,
  },
  buttonTextGhost: {
    color: colors.primary,
  },
  buttonTextSm: {
    fontSize: fontSize.sm,
  },

  // Badge
  badge: {
    paddingVertical: 2,
    paddingHorizontal: spacing.sm,
    borderRadius: borderRadius.full,
    alignSelf: "flex-start",
  },
  badgeText: {
    fontSize: fontSize.xs,
    fontWeight: fontWeight.semibold,
  },

  // Empty state
  emptyState: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: spacing["5xl"],
    paddingHorizontal: spacing["2xl"],
  },
  emptyTitle: {
    fontSize: fontSize.lg,
    fontWeight: fontWeight.medium,
    color: colors.foreground,
    textAlign: "center",
  },
  emptyMessage: {
    fontSize: fontSize.sm,
    color: colors.foregroundMuted,
    textAlign: "center",
    marginTop: spacing.sm,
    lineHeight: 20,
  },
  emptyAction: {
    marginTop: spacing.xl,
  },

  // Loading
  loadingScreen: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.background,
  },

  // Divider
  divider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: colors.border,
  },

  // Section header
  sectionHeader: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
  },
  sectionHeaderText: {
    fontSize: fontSize.xs,
    fontWeight: fontWeight.semibold,
    color: colors.foregroundMuted,
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
});
