/**
 * Task List — grouped by phase, filterable by status.
 */

import React, { useMemo, useState } from "react";
import {
  FlatList,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/hooks/useAuth";
import { Badge, EmptyState, LoadingScreen } from "@/components/ui";
import { TASK_PHASE_LABELS, TASK_PHASE_ORDER, TASK_STATUS_LABELS, TASK_PRIORITY_LABELS } from "@/lib/constants";
import { colors, spacing, fontSize, fontWeight, borderRadius } from "@/lib/theme";
import type { Task, TaskStatus } from "@/lib/types";

const FIRM_ID = "current";

const STATUS_COLORS: Record<string, "green" | "amber" | "red" | "blue" | "gray"> = {
  not_started: "gray",
  in_progress: "blue",
  blocked: "red",
  complete: "green",
  waived: "gray",
  cancelled: "gray",
};

const PRIORITY_ICONS: Record<string, { name: keyof typeof Ionicons.glyphMap; color: string }> = {
  critical: { name: "alert-circle", color: colors.danger },
  normal: { name: "remove-circle-outline", color: colors.foregroundMuted },
  informational: { name: "information-circle-outline", color: colors.info },
};

const FILTER_OPTIONS: { label: string; value: TaskStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Active", value: "in_progress" },
  { label: "Not Started", value: "not_started" },
  { label: "Blocked", value: "blocked" },
  { label: "Complete", value: "complete" },
];

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

// ─── Task Item ──────────────────────────────────────────────────────────────

function TaskItem({ task, onPress }: { task: Task; onPress: () => void }) {
  const priorityIcon = PRIORITY_ICONS[task.priority] ?? PRIORITY_ICONS["normal"];
  const isOverdue = task.due_date && new Date(task.due_date) < new Date() && task.status !== "complete";

  return (
    <Pressable onPress={onPress} style={({ pressed }) => [styles.taskItem, pressed && { opacity: 0.85 }]}>
      <View style={styles.taskLeft}>
        <Ionicons name={priorityIcon.name} size={18} color={priorityIcon.color} />
      </View>
      <View style={styles.taskContent}>
        <Text style={[styles.taskTitle, task.status === "complete" && styles.taskTitleComplete]} numberOfLines={2}>
          {task.title}
        </Text>
        <View style={styles.taskMeta}>
          <Badge label={TASK_STATUS_LABELS[task.status] ?? task.status} color={STATUS_COLORS[task.status] ?? "gray"} />
          {task.due_date && (
            <Text style={[styles.taskDate, isOverdue && { color: colors.danger }]}>
              {isOverdue ? "Overdue: " : "Due: "}{formatDate(task.due_date)}
            </Text>
          )}
        </View>
      </View>
      <Ionicons name="chevron-forward" size={16} color={colors.foregroundLight} />
    </Pressable>
  );
}

// ─── Phase Group ────────────────────────────────────────────────────────────

function PhaseGroup({
  phase,
  tasks,
  onTaskPress,
}: {
  phase: string;
  tasks: Task[];
  onTaskPress: (taskId: string) => void;
}) {
  if (tasks.length === 0) return null;
  return (
    <View style={styles.phaseGroup}>
      <View style={styles.phaseHeader}>
        <Text style={styles.phaseTitle}>{TASK_PHASE_LABELS[phase] ?? phase}</Text>
        <Text style={styles.phaseCount}>{tasks.length}</Text>
      </View>
      {tasks.map((task) => (
        <TaskItem key={task.id} task={task} onPress={() => onTaskPress(task.id)} />
      ))}
    </View>
  );
}

// ─── Main Screen ────────────────────────────────────────────────────────────

interface TaskListScreenProps {
  matterId: string;
  onSelectTask: (taskId: string) => void;
}

export function TaskListScreen({ matterId, onSelectTask }: TaskListScreenProps) {
  const { api } = useAuth();
  const [filter, setFilter] = useState<TaskStatus | "all">("all");

  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ["tasks", FIRM_ID, matterId],
    queryFn: () => api.getTasks(FIRM_ID, matterId, { per_page: 200 }),
  });

  const tasks = data?.data ?? [];

  const filteredTasks = useMemo(() => {
    if (filter === "all") return tasks;
    return tasks.filter((t) => t.status === filter);
  }, [tasks, filter]);

  const groupedByPhase = useMemo(() => {
    const groups: Record<string, Task[]> = {};
    for (const phase of TASK_PHASE_ORDER) {
      const phaseTasks = filteredTasks.filter((t) => t.phase === phase);
      if (phaseTasks.length > 0) {
        groups[phase] = phaseTasks;
      }
    }
    return groups;
  }, [filteredTasks]);

  if (isLoading) return <LoadingScreen />;

  return (
    <View style={styles.container}>
      {/* Filter chips */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.filterScroll}
        contentContainerStyle={styles.filterContent}
      >
        {FILTER_OPTIONS.map((opt) => (
          <Pressable
            key={opt.value}
            onPress={() => setFilter(opt.value)}
            style={[styles.filterChip, filter === opt.value && styles.filterChipActive]}
          >
            <Text style={[styles.filterChipText, filter === opt.value && styles.filterChipTextActive]}>
              {opt.label}
            </Text>
          </Pressable>
        ))}
      </ScrollView>

      {/* Task list */}
      <ScrollView
        style={styles.listContainer}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={colors.primary} />
        }
      >
        {Object.keys(groupedByPhase).length === 0 ? (
          <EmptyState
            title="No tasks"
            message={filter === "all" ? "No tasks for this matter yet." : `No ${filter.replace("_", " ")} tasks.`}
          />
        ) : (
          Object.entries(groupedByPhase).map(([phase, phaseTasks]) => (
            <PhaseGroup key={phase} phase={phase} tasks={phaseTasks} onTaskPress={onSelectTask} />
          ))
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },

  // Filters
  filterScroll: { flexGrow: 0, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border, backgroundColor: colors.surface },
  filterContent: { paddingHorizontal: spacing.lg, paddingVertical: spacing.md, gap: spacing.sm },
  filterChip: {
    paddingHorizontal: spacing.lg, paddingVertical: spacing.sm,
    borderRadius: borderRadius.full, backgroundColor: colors.muted,
  },
  filterChipActive: { backgroundColor: colors.primary },
  filterChipText: { fontSize: fontSize.sm, fontWeight: fontWeight.medium, color: colors.foregroundMuted },
  filterChipTextActive: { color: colors.white },

  // List
  listContainer: { flex: 1 },
  listContent: { padding: spacing.lg, paddingBottom: spacing["5xl"] },

  // Phase group
  phaseGroup: { marginBottom: spacing.xl },
  phaseHeader: {
    flexDirection: "row", justifyContent: "space-between", alignItems: "center",
    marginBottom: spacing.sm, paddingBottom: spacing.xs,
    borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.borderLight,
  },
  phaseTitle: { fontSize: fontSize.xs, fontWeight: fontWeight.semibold, color: colors.foregroundMuted, textTransform: "uppercase", letterSpacing: 0.8 },
  phaseCount: { fontSize: fontSize.xs, color: colors.foregroundLight },

  // Task item
  taskItem: {
    flexDirection: "row", alignItems: "center", gap: spacing.md,
    backgroundColor: colors.surface, borderRadius: borderRadius.lg,
    borderWidth: 1, borderColor: colors.border,
    padding: spacing.md, marginBottom: spacing.sm,
  },
  taskLeft: { width: 24, alignItems: "center" },
  taskContent: { flex: 1, gap: spacing.xs },
  taskTitle: { fontSize: fontSize.sm, fontWeight: fontWeight.medium, color: colors.foreground },
  taskTitleComplete: { textDecorationLine: "line-through", color: colors.foregroundMuted },
  taskMeta: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  taskDate: { fontSize: fontSize.xs, color: colors.foregroundMuted },
});
