/**
 * Matters tab — stack navigator for matter list → detail → tasks → task detail.
 */

import React, { useState } from "react";
import { SafeAreaView, StyleSheet, View, Pressable, Text } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { MattersScreen } from "@/screens/tabs/MattersScreen";
import { MatterDetailScreen } from "@/screens/matter/MatterDetailScreen";
import { TaskListScreen } from "@/screens/matter/TaskListScreen";
import { TaskDetailScreen } from "@/screens/matter/TaskDetailScreen";
import { colors, spacing, fontSize, fontWeight } from "@/lib/theme";

type Screen =
  | { name: "list" }
  | { name: "detail"; matterId: string }
  | { name: "tasks"; matterId: string }
  | { name: "taskDetail"; matterId: string; taskId: string };

function BackButton({ onPress, title }: { onPress: () => void; title: string }) {
  return (
    <View style={styles.navBar}>
      <Pressable onPress={onPress} style={styles.backButton} hitSlop={8}>
        <Ionicons name="chevron-back" size={22} color={colors.primary} />
        <Text style={styles.backText}>Back</Text>
      </Pressable>
      <Text style={styles.navTitle} numberOfLines={1}>{title}</Text>
      <View style={styles.backButton} />
    </View>
  );
}

export default function MattersTab() {
  const [stack, setStack] = useState<Screen[]>([{ name: "list" }]);
  const current = stack[stack.length - 1]!;

  const push = (screen: Screen) => setStack((s) => [...s, screen]);
  const pop = () => setStack((s) => (s.length > 1 ? s.slice(0, -1) : s));

  return (
    <SafeAreaView style={styles.container}>
      {current.name === "list" && (
        <MattersScreen
          onSelectMatter={(matterId) => push({ name: "detail", matterId })}
        />
      )}

      {current.name === "detail" && (
        <>
          <BackButton onPress={pop} title="Matter" />
          <MatterDetailScreen
            matterId={current.matterId}
            onNavigateToTasks={() =>
              push({ name: "tasks", matterId: current.matterId })
            }
          />
        </>
      )}

      {current.name === "tasks" && (
        <>
          <BackButton onPress={pop} title="Tasks" />
          <TaskListScreen
            matterId={current.matterId}
            onSelectTask={(taskId) =>
              push({ name: "taskDetail", matterId: current.matterId, taskId })
            }
          />
        </>
      )}

      {current.name === "taskDetail" && (
        <>
          <BackButton onPress={pop} title="Task" />
          <TaskDetailScreen
            matterId={current.matterId}
            taskId={current.taskId}
            onGoBack={pop}
          />
        </>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  navBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    height: 44,
    paddingHorizontal: spacing.sm,
    backgroundColor: colors.surface,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  backButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 2,
    minWidth: 70,
  },
  backText: {
    fontSize: fontSize.base,
    color: colors.primary,
    fontWeight: fontWeight.medium,
  },
  navTitle: {
    flex: 1,
    fontSize: fontSize.base,
    fontWeight: fontWeight.semibold,
    color: colors.foreground,
    textAlign: "center",
  },
});
