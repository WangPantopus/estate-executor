/**
 * Matters list screen — shows all active matters for the user's firm.
 */

import React from "react";
import {
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/hooks/useAuth";
import { Card, Badge, LoadingScreen, EmptyState } from "@/components/ui";
import { PHASE_LABELS } from "@/lib/constants";
import { colors, spacing, fontSize, fontWeight, borderRadius, shadow } from "@/lib/theme";
import type { Matter } from "@/lib/types";

const FIRM_ID = "current";

function formatCurrency(value: number | null): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function MatterCard({ matter }: { matter: Matter }) {
  const phaseColor =
    matter.phase === "distribution" || matter.phase === "closing"
      ? "green"
      : matter.phase === "administration"
        ? "blue"
        : "amber";

  return (
    <Pressable style={({ pressed }) => [pressed && { opacity: 0.9 }]}>
      <Card style={styles.matterCard}>
        <View style={styles.matterHeader}>
          <View style={styles.matterTitleRow}>
            <Text style={styles.matterTitle} numberOfLines={1}>
              {matter.decedent_name}
            </Text>
            <Badge
              label={PHASE_LABELS[matter.phase] ?? matter.phase}
              color={phaseColor}
            />
          </View>
          <Text style={styles.matterType}>
            {matter.jurisdiction_state} · {matter.estate_type.replace(/_/g, " ")}
          </Text>
        </View>

        <View style={styles.matterFooter}>
          <View style={styles.matterStat}>
            <Text style={styles.matterStatLabel}>Est. Value</Text>
            <Text style={styles.matterStatValue}>
              {formatCurrency(matter.estimated_value)}
            </Text>
          </View>
          <View style={styles.matterStat}>
            <Text style={styles.matterStatLabel}>Status</Text>
            <Text style={[styles.matterStatValue, { textTransform: "capitalize" }]}>
              {matter.status.replace(/_/g, " ")}
            </Text>
          </View>
        </View>
      </Card>
    </Pressable>
  );
}

export function MattersScreen() {
  const { api } = useAuth();

  const {
    data,
    isLoading,
    refetch,
    isRefetching,
  } = useQuery({
    queryKey: ["matters", FIRM_ID],
    queryFn: () => api.getMatters(FIRM_ID),
  });

  if (isLoading) return <LoadingScreen />;

  const matters = data?.data ?? [];

  return (
    <View style={styles.container}>
      <FlatList
        data={matters}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => <MatterCard matter={item} />}
        contentContainerStyle={styles.list}
        ItemSeparatorComponent={() => <View style={{ height: spacing.md }} />}
        refreshControl={
          <RefreshControl
            refreshing={isRefetching}
            onRefresh={refetch}
            tintColor={colors.primary}
          />
        }
        ListEmptyComponent={
          <EmptyState
            title="No matters"
            message="Active matters will appear here."
          />
        }
        ListHeaderComponent={
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Matters</Text>
            <Text style={styles.headerCount}>
              {matters.length} active
            </Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  list: {
    padding: spacing.lg,
    paddingBottom: spacing["4xl"],
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "baseline",
    marginBottom: spacing.lg,
  },
  headerTitle: {
    fontSize: fontSize["2xl"],
    fontWeight: fontWeight.semibold,
    color: colors.foreground,
    letterSpacing: -0.5,
  },
  headerCount: {
    fontSize: fontSize.sm,
    color: colors.foregroundMuted,
  },

  // Matter card
  matterCard: {
    gap: spacing.md,
  },
  matterHeader: {
    gap: spacing.xs,
  },
  matterTitleRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: spacing.sm,
  },
  matterTitle: {
    fontSize: fontSize.lg,
    fontWeight: fontWeight.medium,
    color: colors.foreground,
    flex: 1,
  },
  matterType: {
    fontSize: fontSize.xs,
    color: colors.foregroundMuted,
    textTransform: "capitalize",
  },
  matterFooter: {
    flexDirection: "row",
    gap: spacing.xl,
    paddingTop: spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.borderLight,
  },
  matterStat: {
    gap: 2,
  },
  matterStatLabel: {
    fontSize: fontSize.xs,
    color: colors.foregroundMuted,
  },
  matterStatValue: {
    fontSize: fontSize.sm,
    fontWeight: fontWeight.medium,
    color: colors.foreground,
  },
});
