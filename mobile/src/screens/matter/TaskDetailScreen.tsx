/**
 * Task Detail — full info, complete/waive actions, document upload.
 */

import React, { useState } from "react";
import {
  Alert,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/hooks/useAuth";
import { Badge, Button, Card, Divider, LoadingScreen } from "@/components/ui";
import { DocumentUpload } from "@/components/DocumentUpload";
import { TASK_STATUS_LABELS, TASK_PHASE_LABELS, TASK_PRIORITY_LABELS } from "@/lib/constants";
import { colors, spacing, fontSize, fontWeight, borderRadius } from "@/lib/theme";

const FIRM_ID = "current";

const STATUS_COLORS: Record<string, "green" | "amber" | "red" | "blue" | "gray"> = {
  not_started: "gray",
  in_progress: "blue",
  blocked: "red",
  complete: "green",
  waived: "gray",
  cancelled: "gray",
};

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

// ─── Info Row ───────────────────────────────────────────────────────────────

function InfoRow({
  icon,
  label,
  value,
  valueColor,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  value: string;
  valueColor?: string;
}) {
  return (
    <View style={styles.infoRow}>
      <Ionicons name={icon} size={16} color={colors.foregroundMuted} />
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={[styles.infoValue, valueColor ? { color: valueColor } : undefined]}>
        {value}
      </Text>
    </View>
  );
}

// ─── Main Screen ────────────────────────────────────────────────────────────

interface TaskDetailScreenProps {
  matterId: string;
  taskId: string;
  onGoBack: () => void;
}

export function TaskDetailScreen({ matterId, taskId, onGoBack }: TaskDetailScreenProps) {
  const { api } = useAuth();
  const qc = useQueryClient();
  const [completionNotes, setCompletionNotes] = useState("");
  const [waiveReason, setWaiveReason] = useState("");
  const [showWaive, setShowWaive] = useState(false);

  const { data: task, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ["task", FIRM_ID, matterId, taskId],
    queryFn: () => api.getTask(FIRM_ID, matterId, taskId),
  });

  const completeMutation = useMutation({
    mutationFn: () => api.completeTask(FIRM_ID, matterId, taskId, completionNotes || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["task", FIRM_ID, matterId, taskId] });
      qc.invalidateQueries({ queryKey: ["tasks", FIRM_ID, matterId] });
      qc.invalidateQueries({ queryKey: ["matterDashboard", FIRM_ID, matterId] });
      Alert.alert("Task Completed", "The task has been marked as complete.");
    },
    onError: (err: Error) => {
      Alert.alert("Error", err.message);
    },
  });

  const waiveMutation = useMutation({
    mutationFn: () => api.waiveTask(FIRM_ID, matterId, taskId, waiveReason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["task", FIRM_ID, matterId, taskId] });
      qc.invalidateQueries({ queryKey: ["tasks", FIRM_ID, matterId] });
      qc.invalidateQueries({ queryKey: ["matterDashboard", FIRM_ID, matterId] });
      setShowWaive(false);
      Alert.alert("Task Waived", "The task has been waived.");
    },
    onError: (err: Error) => {
      Alert.alert("Error", err.message);
    },
  });

  const handleComplete = () => {
    Alert.alert("Complete Task", "Mark this task as complete?", [
      { text: "Cancel", style: "cancel" },
      { text: "Complete", onPress: () => completeMutation.mutate() },
    ]);
  };

  const handleWaive = () => {
    if (!waiveReason.trim()) {
      Alert.alert("Reason required", "Please provide a reason for waiving this task.");
      return;
    }
    waiveMutation.mutate();
  };

  if (isLoading) return <LoadingScreen />;
  if (!task) return null;

  const canComplete = task.status === "not_started" || task.status === "in_progress";
  const canWaive = task.status !== "complete" && task.status !== "waived" && task.status !== "cancelled";
  const isOverdue = task.due_date && new Date(task.due_date) < new Date() && task.status !== "complete";

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={colors.primary} />
      }
    >
      {/* Header */}
      <Card style={styles.headerCard}>
        <View style={styles.headerBadges}>
          <Badge
            label={TASK_STATUS_LABELS[task.status] ?? task.status}
            color={STATUS_COLORS[task.status] ?? "gray"}
          />
          <Badge
            label={TASK_PRIORITY_LABELS[task.priority] ?? task.priority}
            color={task.priority === "critical" ? "red" : task.priority === "normal" ? "blue" : "gray"}
          />
        </View>
        <Text style={styles.taskTitle}>{task.title}</Text>
        {task.description && (
          <Text style={styles.taskDescription}>{task.description}</Text>
        )}
      </Card>

      {/* Details */}
      <Card>
        <Text style={styles.sectionTitle}>Details</Text>
        <InfoRow icon="layers-outline" label="Phase" value={TASK_PHASE_LABELS[task.phase] ?? task.phase} />
        <Divider />
        <InfoRow
          icon="calendar-outline"
          label="Due Date"
          value={formatDate(task.due_date)}
          valueColor={isOverdue ? colors.danger : undefined}
        />
        <Divider />
        <InfoRow icon="time-outline" label="Created" value={formatDate(task.created_at)} />
        {task.completed_at && (
          <>
            <Divider />
            <InfoRow icon="checkmark-circle-outline" label="Completed" value={formatDate(task.completed_at)} valueColor={colors.success} />
          </>
        )}
        {task.requires_document && (
          <>
            <Divider />
            <InfoRow
              icon="document-attach-outline"
              label="Document Required"
              value={task.documents.length > 0 ? `${task.documents.length} attached` : "Yes — none attached"}
              valueColor={task.documents.length > 0 ? colors.success : colors.warning}
            />
          </>
        )}
      </Card>

      {/* Instructions */}
      {task.instructions && (
        <Card>
          <Text style={styles.sectionTitle}>Instructions</Text>
          <Text style={styles.instructionsText}>{task.instructions}</Text>
        </Card>
      )}

      {/* Documents */}
      {task.documents.length > 0 && (
        <Card>
          <Text style={styles.sectionTitle}>Attached Documents</Text>
          {task.documents.map((doc) => (
            <View key={doc.id} style={styles.docRow}>
              <Ionicons name="document-outline" size={16} color={colors.foregroundMuted} />
              <Text style={styles.docName} numberOfLines={1}>{doc.filename}</Text>
              <Text style={styles.docType}>{doc.doc_type ?? "—"}</Text>
            </View>
          ))}
        </Card>
      )}

      {/* Document upload */}
      {canComplete && (
        <DocumentUpload
          firmId={FIRM_ID}
          matterId={matterId}
          taskId={taskId}
          onUploaded={() => refetch()}
        />
      )}

      {/* Actions */}
      {(canComplete || canWaive) && (
        <Card>
          <Text style={styles.sectionTitle}>Actions</Text>

          {canComplete && (
            <>
              <TextInput
                style={styles.notesInput}
                placeholder="Completion notes (optional)"
                value={completionNotes}
                onChangeText={setCompletionNotes}
                multiline
                placeholderTextColor={colors.foregroundLight}
              />
              <Button
                title="Complete Task"
                variant="primary"
                onPress={handleComplete}
                loading={completeMutation.isPending}
                icon={<Ionicons name="checkmark-circle" size={18} color={colors.white} />}
              />
            </>
          )}

          {canWaive && (
            <View style={styles.waiveSection}>
              {showWaive ? (
                <>
                  <TextInput
                    style={styles.notesInput}
                    placeholder="Reason for waiving (required)"
                    value={waiveReason}
                    onChangeText={setWaiveReason}
                    multiline
                    placeholderTextColor={colors.foregroundLight}
                  />
                  <View style={styles.waiveButtons}>
                    <Button
                      title="Cancel"
                      variant="ghost"
                      size="sm"
                      onPress={() => setShowWaive(false)}
                    />
                    <Button
                      title="Confirm Waive"
                      variant="outline"
                      size="sm"
                      onPress={handleWaive}
                      loading={waiveMutation.isPending}
                    />
                  </View>
                </>
              ) : (
                <Button
                  title="Waive Task"
                  variant="ghost"
                  size="sm"
                  onPress={() => setShowWaive(true)}
                />
              )}
            </View>
          )}
        </Card>
      )}

      {/* Comments */}
      {task.comments && task.comments.length > 0 && (
        <Card>
          <Text style={styles.sectionTitle}>Comments</Text>
          {task.comments.map((comment) => (
            <View key={comment.id} style={styles.commentRow}>
              <Text style={styles.commentBody}>{comment.body}</Text>
              <Text style={styles.commentMeta}>{formatDate(comment.created_at)}</Text>
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
  headerBadges: { flexDirection: "row", gap: spacing.sm },
  taskTitle: { fontSize: fontSize.xl, fontWeight: fontWeight.semibold, color: colors.foreground },
  taskDescription: { fontSize: fontSize.sm, color: colors.foregroundMuted, lineHeight: 20 },

  sectionTitle: { fontSize: fontSize.xs, fontWeight: fontWeight.semibold, color: colors.foregroundMuted, textTransform: "uppercase", letterSpacing: 0.8, marginBottom: spacing.md },

  infoRow: { flexDirection: "row", alignItems: "center", paddingVertical: spacing.sm, gap: spacing.sm },
  infoLabel: { fontSize: fontSize.sm, color: colors.foregroundMuted, width: 100 },
  infoValue: { flex: 1, fontSize: fontSize.sm, fontWeight: fontWeight.medium, color: colors.foreground, textAlign: "right" },

  instructionsText: { fontSize: fontSize.sm, color: colors.foreground, lineHeight: 22 },

  docRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm, paddingVertical: spacing.sm },
  docName: { flex: 1, fontSize: fontSize.sm, color: colors.foreground },
  docType: { fontSize: fontSize.xs, color: colors.foregroundMuted },

  notesInput: {
    borderWidth: 1, borderColor: colors.border, borderRadius: borderRadius.md,
    padding: spacing.md, fontSize: fontSize.sm, color: colors.foreground,
    minHeight: 60, textAlignVertical: "top", marginBottom: spacing.md,
  },

  waiveSection: { marginTop: spacing.md, paddingTop: spacing.md, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.borderLight },
  waiveButtons: { flexDirection: "row", gap: spacing.sm, justifyContent: "flex-end" },

  commentRow: { paddingVertical: spacing.sm, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.borderLight },
  commentBody: { fontSize: fontSize.sm, color: colors.foreground },
  commentMeta: { fontSize: fontSize.xs, color: colors.foregroundLight, marginTop: 2 },
});
