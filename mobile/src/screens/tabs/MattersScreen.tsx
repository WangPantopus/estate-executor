/**
 * Matters list screen — cards with status, progress bar, next deadline.
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
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "@/hooks/useAuth";
import { useOfflineQuery } from "@/hooks/useOfflineQuery";
import { mattersCacheKey } from "@/lib/offline-cache";
import { Card, Badge, LoadingScreen, EmptyState } from "@/components/ui";
import { PHASE_LABELS } from "@/lib/constants";
import { colors, spacing, fontSize, fontWeight, borderRadius } from "@/lib/theme";
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

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

// We use portfolio-style data when available; fallback to basic matter data.
// The portfolio endpoint provides task counts and deadlines per matter.

interface MatterWithProgress extends Matter {
  _taskComplete?: number;
  _taskTotal?: number;
  _nextDeadline?: string | null;
  _overdueCount?: number;
}

function MatterCard({ matter, onPress }: { matter: MatterWithProgress; onPress: () => void }) {
  const phaseColor: "green" | "amber" | "blue" =
    matter.phase === "distribution" || matter.phase === "closing"
      ? "green"
      : matter.phase === "administration"
        ? "blue"
        : "amber";

  // Simulated progress — in production comes from portfolio endpoint
  const completePct = matter._taskTotal
    ? Math.round(((matter._taskComplete ?? 0) / matter._taskTotal) * 100)
    : null;

  return (
    <Pressable onPress={onPress} style={({ pressed }) => [pressed && { opacity: 0.9 }]}>
      <Card style={styles.matterCard}>
        {/* Title row */}
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

        {/* Progress bar */}
        {completePct != null && (
          <View style={styles.progressSection}>
            <View style={styles.progressBar}>
              <View
                style={[
                  styles.progressFill,
                  {
                    width: `${completePct}%`,
                    backgroundColor: completePct >= 75 ? colors.success : completePct >= 40 ? colors.gold : colors.info,
                  },
                ]}
              />
            </View>
            <Text style={styles.progressLabel}>{completePct}% complete</Text>
          </View>
        )}

        {/* Footer stats */}
        <View style={styles.matterFooter}>
          <View style={styles.matterStat}>
            <Text style={styles.matterStatLabel}>Est. Value</Text>
            <Text style={styles.matterStatValue}>
              {formatCurrency(matter.estimated_value)}
            </Text>
          </View>
          {matter._nextDeadline && (
            <View style={styles.matterStat}>
              <Text style={styles.matterStatLabel}>Next Deadline</Text>
              <View style={styles.deadlineRow}>
                <Ionicons name="calendar-outline" size={12} color={colors.warning} />
                <Text style={styles.deadlineText}>{formatDate(matter._nextDeadline)}</Text>
              </View>
            </View>
          )}
          {(matter._overdueCount ?? 0) > 0 && (
            <View style={styles.matterStat}>
              <Text style={styles.matterStatLabel}>Overdue</Text>
              <Text style={[styles.matterStatValue, { color: colors.danger }]}>
                {matter._overdueCount}
              </Text>
            </View>
          )}
        </View>
      </Card>
    </Pressable>
  );
}

interface MattersScreenProps {
  onSelectMatter?: (matterId: string) => void;
}

export function MattersScreen({ onSelectMatter }: MattersScreenProps) {
  const { api } = useAuth();

  const {
    data,
    isLoading,
    refetch,
    isRefetching,
  } = useOfflineQuery({
    queryKey: ["matters", FIRM_ID],
    queryFn: () => api.getMatters(FIRM_ID),
    cacheKey: mattersCacheKey(FIRM_ID),
  });

  if (isLoading) return <LoadingScreen />;

  const matters: MatterWithProgress[] = data?.data ?? [];

  return (
    <View style={styles.container}>
      <FlatList
        data={matters}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <MatterCard
            matter={item}
            onPress={() => onSelectMatter?.(item.id)}
          />
        )}
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
  container: { flex: 1, backgroundColor: colors.background },
  list: { padding: spacing.lg, paddingBottom: spacing["4xl"] },
  header: {
    flexDirection: "row", justifyContent: "space-between", alignItems: "baseline",
    marginBottom: spacing.lg,
  },
  headerTitle: { fontSize: fontSize["2xl"], fontWeight: fontWeight.semibold, color: colors.foreground, letterSpacing: -0.5 },
  headerCount: { fontSize: fontSize.sm, color: colors.foregroundMuted },

  matterCard: { gap: spacing.md },
  matterHeader: { gap: spacing.xs },
  matterTitleRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: spacing.sm },
  matterTitle: { fontSize: fontSize.lg, fontWeight: fontWeight.medium, color: colors.foreground, flex: 1 },
  matterType: { fontSize: fontSize.xs, color: colors.foregroundMuted, textTransform: "capitalize" },

  // Progress
  progressSection: { gap: spacing.xs },
  progressBar: { height: 6, backgroundColor: colors.muted, borderRadius: 3, overflow: "hidden" },
  progressFill: { height: "100%", borderRadius: 3 },
  progressLabel: { fontSize: fontSize.xs, color: colors.foregroundMuted },

  // Footer
  matterFooter: {
    flexDirection: "row", gap: spacing.xl, paddingTop: spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.borderLight,
  },
  matterStat: { gap: 2 },
  matterStatLabel: { fontSize: fontSize.xs, color: colors.foregroundMuted },
  matterStatValue: { fontSize: fontSize.sm, fontWeight: fontWeight.medium, color: colors.foreground },
  deadlineRow: { flexDirection: "row", alignItems: "center", gap: 4 },
  deadlineText: { fontSize: fontSize.sm, fontWeight: fontWeight.medium, color: colors.warning },
});
