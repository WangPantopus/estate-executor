/**
 * Notifications screen — deadline alerts, task updates, communications.
 */

import React, { useMemo } from "react";
import {
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Card, EmptyState, LoadingScreen, Badge } from "@/components/ui";
import { colors, spacing, fontSize, fontWeight, borderRadius } from "@/lib/theme";
import type { AppNotification } from "@/lib/types";

// Placeholder notifications — in production these come from a backend endpoint
// or push notification history.
const MOCK_NOTIFICATIONS: AppNotification[] = [
  {
    id: "1",
    title: "Deadline approaching",
    body: "IRS Form 706 due in 5 days",
    type: "deadline",
    matter_id: "matter-1",
    matter_title: "Estate of John Doe",
    created_at: new Date().toISOString(),
    read: false,
  },
  {
    id: "2",
    title: "Task completed",
    body: "Inventory of personal property marked complete",
    type: "task",
    matter_id: "matter-1",
    matter_title: "Estate of John Doe",
    created_at: new Date(Date.now() - 3600000).toISOString(),
    read: false,
  },
  {
    id: "3",
    title: "New message",
    body: "Beneficiary Jane Doe sent a question about distribution timeline",
    type: "communication",
    matter_id: "matter-1",
    matter_title: "Estate of John Doe",
    created_at: new Date(Date.now() - 86400000).toISOString(),
    read: true,
  },
];

const TYPE_CONFIG: Record<string, { icon: keyof typeof Ionicons.glyphMap; color: string }> = {
  deadline: { icon: "calendar-outline", color: colors.warning },
  task: { icon: "checkmark-circle-outline", color: colors.success },
  communication: { icon: "chatbubble-outline", color: colors.info },
  distribution: { icon: "wallet-outline", color: colors.gold },
};

function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function NotificationItem({ notification }: { notification: AppNotification }) {
  const config = TYPE_CONFIG[notification.type] ?? TYPE_CONFIG["task"];

  return (
    <Pressable style={({ pressed }) => [pressed && { opacity: 0.85 }]}>
      <View
        style={[
          styles.notifItem,
          !notification.read && styles.notifUnread,
        ]}
      >
        <View style={[styles.notifIcon, { backgroundColor: config.color + "18" }]}>
          <Ionicons name={config.icon} size={20} color={config.color} />
        </View>
        <View style={styles.notifContent}>
          <View style={styles.notifTitleRow}>
            <Text style={styles.notifTitle} numberOfLines={1}>
              {notification.title}
            </Text>
            <Text style={styles.notifTime}>
              {formatTimeAgo(notification.created_at)}
            </Text>
          </View>
          <Text style={styles.notifBody} numberOfLines={2}>
            {notification.body}
          </Text>
          <Text style={styles.notifMatter}>{notification.matter_title}</Text>
        </View>
        {!notification.read && <View style={styles.unreadDot} />}
      </View>
    </Pressable>
  );
}

export function NotificationsScreen() {
  const notifications = MOCK_NOTIFICATIONS;
  const unreadCount = useMemo(
    () => notifications.filter((n) => !n.read).length,
    [notifications],
  );

  return (
    <View style={styles.container}>
      <FlatList
        data={notifications}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => <NotificationItem notification={item} />}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <EmptyState
            title="No notifications"
            message="You're all caught up. Notifications about deadlines, tasks, and messages will appear here."
          />
        }
        ListHeaderComponent={
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Notifications</Text>
            {unreadCount > 0 && (
              <Badge label={`${unreadCount} new`} color="blue" />
            )}
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
    alignItems: "center",
    marginBottom: spacing.lg,
  },
  headerTitle: {
    fontSize: fontSize["2xl"],
    fontWeight: fontWeight.semibold,
    color: colors.foreground,
    letterSpacing: -0.5,
  },

  // Notification item
  notifItem: {
    flexDirection: "row",
    alignItems: "flex-start",
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: spacing.sm,
    gap: spacing.md,
  },
  notifUnread: {
    backgroundColor: colors.infoLight,
    borderColor: colors.info + "30",
  },
  notifIcon: {
    width: 40,
    height: 40,
    borderRadius: borderRadius.md,
    alignItems: "center",
    justifyContent: "center",
  },
  notifContent: {
    flex: 1,
    gap: 3,
  },
  notifTitleRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  notifTitle: {
    fontSize: fontSize.sm,
    fontWeight: fontWeight.semibold,
    color: colors.foreground,
    flex: 1,
  },
  notifTime: {
    fontSize: fontSize.xs,
    color: colors.foregroundLight,
    marginLeft: spacing.sm,
  },
  notifBody: {
    fontSize: fontSize.sm,
    color: colors.foregroundMuted,
    lineHeight: 18,
  },
  notifMatter: {
    fontSize: fontSize.xs,
    color: colors.foregroundLight,
    marginTop: 2,
  },
  unreadDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.info,
    marginTop: 6,
  },
});
