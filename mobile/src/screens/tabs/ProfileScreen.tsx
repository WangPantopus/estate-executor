/**
 * Profile screen — user info, firm membership, settings, logout.
 */

import React from "react";
import { Alert, ScrollView, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Card, Button, Divider } from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";
import { colors, spacing, fontSize, fontWeight, borderRadius } from "@/lib/theme";

function ProfileRow({
  icon,
  label,
  value,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  value: string;
}) {
  return (
    <View style={styles.row}>
      <View style={styles.rowIcon}>
        <Ionicons name={icon} size={18} color={colors.foregroundMuted} />
      </View>
      <View style={styles.rowContent}>
        <Text style={styles.rowLabel}>{label}</Text>
        <Text style={styles.rowValue}>{value}</Text>
      </View>
    </View>
  );
}

export function ProfileScreen() {
  const { user, logout } = useAuth();

  const handleLogout = () => {
    Alert.alert("Log Out", "Are you sure you want to log out?", [
      { text: "Cancel", style: "cancel" },
      { text: "Log Out", style: "destructive", onPress: logout },
    ]);
  };

  const initials = (user?.full_name ?? "U")
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
    >
      {/* Avatar & name */}
      <View style={styles.header}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{initials}</Text>
        </View>
        <Text style={styles.name}>{user?.full_name ?? "User"}</Text>
        <Text style={styles.email}>{user?.email ?? ""}</Text>
      </View>

      {/* Account section */}
      <Card>
        <Text style={styles.sectionTitle}>Account</Text>
        <ProfileRow icon="mail-outline" label="Email" value={user?.email ?? "—"} />
        <Divider />
        <ProfileRow icon="person-outline" label="Name" value={user?.full_name ?? "—"} />
      </Card>

      {/* Firm memberships */}
      {user?.firm_memberships && user.firm_memberships.length > 0 && (
        <Card>
          <Text style={styles.sectionTitle}>Firm Memberships</Text>
          {user.firm_memberships.map((fm, i) => (
            <React.Fragment key={fm.firm_id}>
              {i > 0 && <Divider />}
              <ProfileRow
                icon="business-outline"
                label={fm.firm_name}
                value={fm.firm_role.charAt(0).toUpperCase() + fm.firm_role.slice(1)}
              />
            </React.Fragment>
          ))}
        </Card>
      )}

      {/* App info */}
      <Card>
        <Text style={styles.sectionTitle}>App</Text>
        <ProfileRow icon="information-circle-outline" label="Version" value="1.0.0" />
        <Divider />
        <ProfileRow icon="shield-checkmark-outline" label="Security" value="SOC 2 Compliant" />
      </Card>

      {/* Logout */}
      <Button
        title="Log Out"
        variant="outline"
        onPress={handleLogout}
        style={styles.logoutButton}
      />

      <Text style={styles.footer}>
        Estate Executor OS
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    padding: spacing.lg,
    paddingBottom: spacing["5xl"],
    gap: spacing.lg,
  },

  // Header
  header: {
    alignItems: "center",
    paddingVertical: spacing.xl,
  },
  avatar: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.md,
  },
  avatarText: {
    fontSize: fontSize["2xl"],
    fontWeight: fontWeight.semibold,
    color: colors.white,
  },
  name: {
    fontSize: fontSize.xl,
    fontWeight: fontWeight.semibold,
    color: colors.foreground,
  },
  email: {
    fontSize: fontSize.sm,
    color: colors.foregroundMuted,
    marginTop: 2,
  },

  // Section
  sectionTitle: {
    fontSize: fontSize.xs,
    fontWeight: fontWeight.semibold,
    color: colors.foregroundMuted,
    textTransform: "uppercase",
    letterSpacing: 0.8,
    marginBottom: spacing.md,
  },

  // Row
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: spacing.md,
    gap: spacing.md,
  },
  rowIcon: {
    width: 32,
    height: 32,
    borderRadius: borderRadius.sm,
    backgroundColor: colors.muted,
    alignItems: "center",
    justifyContent: "center",
  },
  rowContent: {
    flex: 1,
  },
  rowLabel: {
    fontSize: fontSize.xs,
    color: colors.foregroundMuted,
  },
  rowValue: {
    fontSize: fontSize.sm,
    fontWeight: fontWeight.medium,
    color: colors.foreground,
    marginTop: 1,
  },

  logoutButton: {
    borderColor: colors.danger + "40",
  },

  footer: {
    fontSize: fontSize.xs,
    color: colors.foregroundLight,
    textAlign: "center",
    marginTop: spacing.sm,
  },
});
