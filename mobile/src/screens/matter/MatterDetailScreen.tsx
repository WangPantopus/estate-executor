/**
 * Matter Detail — simplified dashboard with stacked cards.
 * Shows matter info, task progress, upcoming deadlines, recent activity.
 */

import React from "react";
import {
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "@/hooks/useAuth";
import { useOfflineQuery } from "@/hooks/useOfflineQuery";
import { matterDetailCacheKey } from "@/lib/offline-cache";
import { Card, Badge, LoadingScreen } from "@/components/ui";
import { PHASE_LABELS } from "@/lib/constants";
import { colors, spacing, fontSize, fontWeight, borderRadius } from "@/lib/theme";
import type { MatterDashboard, DeadlineResponse } from "@/lib/types";

const FIRM_ID = "current";

function formatCurrency(value: number | null): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

// ─── Progress Ring ──────────────────────────────────────────────────────────

function ProgressRing({ percentage }: { percentage: number }) {
  const clampedPct = Math.min(100, Math.max(0, percentage));
  return (
    <View style={styles.progressRing}>
      <View style={[styles.progressTrack, { backgroundColor: colors.muted }]}>
        <View
          style={[
            styles.progressFill,
            {
              width: `${clampedPct}%`,
              backgroundColor: clampedPct >= 75 ? colors.success : clampedPct >= 40 ? colors.gold : colors.info,
            },
          ]}
        />
      </View>
      <Text style={styles.progressText}>{Math.round(clampedPct)}%</Text>
    </View>
  );
}

// ─── Stat Card ──────────────────────────────────────────────────────────────

function StatCard({
  icon,
  iconColor,
  label,
  value,
  subvalue,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  iconColor: string;
  label: string;
  value: string;
  subvalue?: string;
}) {
  return (
    <View style={styles.statCard}>
      <View style={[styles.statIcon, { backgroundColor: iconColor + "18" }]}>
        <Ionicons name={icon} size={18} color={iconColor} />
      </View>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={styles.statValue}>{value}</Text>
      {subvalue && <Text style={styles.statSubvalue}>{subvalue}</Text>}
    </View>
  );
}

// ─── Deadline Row ───────────────────────────────────────────────────────────

function DeadlineRow({ deadline }: { deadline: DeadlineResponse }) {
  const isOverdue = new Date(deadline.due_date) < new Date() && deadline.status !== "completed";
  return (
    <View style={styles.deadlineRow}>
      <View style={[styles.deadlineDot, { backgroundColor: isOverdue ? colors.danger : colors.warning }]} />
      <View style={styles.deadlineContent}>
        <Text style={styles.deadlineTitle} numberOfLines={1}>{deadline.title}</Text>
        <Text style={[styles.deadlineDate, isOverdue && { color: colors.danger }]}>
          {formatDate(deadline.due_date)}
          {isOverdue && " — Overdue"}
        </Text>
      </View>
    </View>
  );
}

// ─── Main Screen ────────────────────────────────────────────────────────────

interface MatterDetailScreenProps {
  matterId: string;
  onNavigateToTasks: () => void;
}

export function MatterDetailScreen({ matterId, onNavigateToTasks }: MatterDetailScreenProps) {
  const { api } = useAuth();

  const { data, isLoading, refetch, isRefetching } = useOfflineQuery({
    queryKey: ["matterDashboard", FIRM_ID, matterId],
    queryFn: () => api.getMatterDashboard(FIRM_ID, matterId),
    cacheKey: matterDetailCacheKey(FIRM_ID, matterId),
  });

  if (isLoading) return <LoadingScreen />;
  if (!data) return null;

  const { matter, task_summary, asset_summary, stakeholder_count, upcoming_deadlines, recent_events } = data;
  const phaseColor = matter.phase === "distribution" || matter.phase === "closing" ? "green" : "blue";

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={colors.primary} />
      }
    >
      {/* Matter header */}
      <Card style={styles.headerCard}>
        <View style={styles.headerTop}>
          <Text style={styles.matterTitle}>{matter.decedent_name}</Text>
          <Badge label={PHASE_LABELS[matter.phase] ?? matter.phase} color={phaseColor} />
        </View>
        <Text style={styles.matterSubtitle}>
          {matter.jurisdiction_state} · {matter.estate_type.replace(/_/g, " ")}
        </Text>
        {matter.estimated_value != null && (
          <Text style={styles.matterValue}>
            Est. Value: {formatCurrency(matter.estimated_value)}
          </Text>
        )}
      </Card>

      {/* Task progress */}
      <Card>
        <Pressable onPress={onNavigateToTasks} style={({ pressed }) => [pressed && { opacity: 0.85 }]}>
          <View style={styles.taskProgressHeader}>
            <Text style={styles.sectionTitle}>Tasks</Text>
            <View style={styles.viewAllRow}>
              <Text style={styles.viewAllText}>View All</Text>
              <Ionicons name="chevron-forward" size={14} color={colors.primary} />
            </View>
          </View>
          <ProgressRing percentage={task_summary.completion_percentage} />
          <View style={styles.taskStats}>
            <View style={styles.taskStat}>
              <Text style={styles.taskStatNum}>{task_summary.complete}</Text>
              <Text style={styles.taskStatLabel}>Done</Text>
            </View>
            <View style={styles.taskStat}>
              <Text style={styles.taskStatNum}>{task_summary.in_progress}</Text>
              <Text style={styles.taskStatLabel}>Active</Text>
            </View>
            <View style={styles.taskStat}>
              <Text style={[styles.taskStatNum, task_summary.overdue > 0 && { color: colors.danger }]}>
                {task_summary.overdue}
              </Text>
              <Text style={styles.taskStatLabel}>Overdue</Text>
            </View>
            <View style={styles.taskStat}>
              <Text style={styles.taskStatNum}>{task_summary.blocked}</Text>
              <Text style={styles.taskStatLabel}>Blocked</Text>
            </View>
          </View>
        </Pressable>
      </Card>

      {/* Quick stats */}
      <View style={styles.statsGrid}>
        <StatCard
          icon="wallet-outline"
          iconColor={colors.success}
          label="Assets"
          value={String(asset_summary.total_count)}
          subvalue={formatCurrency(asset_summary.total_estimated_value)}
        />
        <StatCard
          icon="people-outline"
          iconColor={colors.info}
          label="Stakeholders"
          value={String(stakeholder_count)}
        />
      </View>

      {/* Upcoming deadlines */}
      {upcoming_deadlines.length > 0 && (
        <Card>
          <Text style={styles.sectionTitle}>Upcoming Deadlines</Text>
          <View style={styles.deadlineList}>
            {upcoming_deadlines.slice(0, 5).map((d) => (
              <DeadlineRow key={d.id} deadline={d} />
            ))}
          </View>
        </Card>
      )}

      {/* Recent activity */}
      {recent_events.length > 0 && (
        <Card>
          <Text style={styles.sectionTitle}>Recent Activity</Text>
          {recent_events.slice(0, 5).map((event) => (
            <View key={event.id} style={styles.eventRow}>
              <Text style={styles.eventAction}>
                {event.action.replace(/_/g, " ")}
              </Text>
              <Text style={styles.eventMeta}>
                {event.actor_name ?? "System"} · {formatDate(event.created_at)}
              </Text>
            </View>
          ))}
        </Card>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: spacing["5xl"], gap: spacing.lg },

  headerCard: { gap: spacing.sm },
  headerTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  matterTitle: { fontSize: fontSize.xl, fontWeight: fontWeight.semibold, color: colors.foreground, flex: 1 },
  matterSubtitle: { fontSize: fontSize.sm, color: colors.foregroundMuted, textTransform: "capitalize" },
  matterValue: { fontSize: fontSize.sm, fontWeight: fontWeight.medium, color: colors.foreground, marginTop: spacing.xs },

  sectionTitle: { fontSize: fontSize.sm, fontWeight: fontWeight.semibold, color: colors.foreground, marginBottom: spacing.md },
  taskProgressHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  viewAllRow: { flexDirection: "row", alignItems: "center", gap: 2 },
  viewAllText: { fontSize: fontSize.sm, color: colors.primary, fontWeight: fontWeight.medium },

  progressRing: { flexDirection: "row", alignItems: "center", gap: spacing.md, marginBottom: spacing.md },
  progressTrack: { flex: 1, height: 8, borderRadius: 4, overflow: "hidden" },
  progressFill: { height: "100%", borderRadius: 4 },
  progressText: { fontSize: fontSize.lg, fontWeight: fontWeight.semibold, color: colors.foreground, minWidth: 44, textAlign: "right" },

  taskStats: { flexDirection: "row", justifyContent: "space-between" },
  taskStat: { alignItems: "center", gap: 2 },
  taskStatNum: { fontSize: fontSize.lg, fontWeight: fontWeight.semibold, color: colors.foreground },
  taskStatLabel: { fontSize: fontSize.xs, color: colors.foregroundMuted },

  statsGrid: { flexDirection: "row", gap: spacing.md },
  statCard: {
    flex: 1, backgroundColor: colors.surface, borderRadius: borderRadius.lg,
    borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.xs,
  },
  statIcon: { width: 36, height: 36, borderRadius: borderRadius.md, alignItems: "center", justifyContent: "center", marginBottom: spacing.xs },
  statLabel: { fontSize: fontSize.xs, color: colors.foregroundMuted },
  statValue: { fontSize: fontSize.xl, fontWeight: fontWeight.semibold, color: colors.foreground },
  statSubvalue: { fontSize: fontSize.xs, color: colors.foregroundMuted },

  deadlineList: { gap: spacing.md },
  deadlineRow: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  deadlineDot: { width: 8, height: 8, borderRadius: 4 },
  deadlineContent: { flex: 1, gap: 1 },
  deadlineTitle: { fontSize: fontSize.sm, fontWeight: fontWeight.medium, color: colors.foreground },
  deadlineDate: { fontSize: fontSize.xs, color: colors.foregroundMuted },

  eventRow: { paddingVertical: spacing.sm, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.borderLight },
  eventAction: { fontSize: fontSize.sm, color: colors.foreground, textTransform: "capitalize" },
  eventMeta: { fontSize: fontSize.xs, color: colors.foregroundLight, marginTop: 2 },
});
