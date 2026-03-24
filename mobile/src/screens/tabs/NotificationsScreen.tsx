/**
 * Notifications screen — shows push notification history with deep link support.
 */

import React from "react";
import {
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { EmptyState, Badge, Button } from "@/components/ui";
import { useNotifications } from "@/hooks/useNotifications";
import { colors, spacing, fontSize, fontWeight, borderRadius } from "@/lib/theme";
import type { AppNotification } from "@/lib/types";

const TYPE_CONFIG: Record<string, { icon: keyof typeof Ionicons.glyphMap; color: string }> = {
  deadline: { icon: "calendar-outline", color: colors.warning },
  task: { icon: "checkmark-circle-outline", color: colors.success },
  communication: { icon: "chatbubble-outline", color: colors.info },
  distribution: { icon: "wallet-outline", color: colors.gold },
};

function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function NotificationItem({
  notification,
  onPress,
}: {
  notification: AppNotification;
  onPress: () => void;
}) {
  const config = TYPE_CONFIG[notification.type] ?? TYPE_CONFIG["task"]!;

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [pressed && { opacity: 0.85 }]}
    >
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
          {notification.matter_title ? (
            <Text style={styles.notifMatter}>{notification.matter_title}</Text>
          ) : null}
        </View>
        {!notification.read && <View style={styles.unreadDot} />}
      </View>
    </Pressable>
  );
}

interface NotificationsScreenProps {
  onNavigateToMatter?: (matterId: string) => void;
}

export function NotificationsScreen({ onNavigateToMatter }: NotificationsScreenProps) {
  const {
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    clearAll,
  } = useNotifications();

  const handlePress = (notification: AppNotification) => {
    markAsRead(notification.id);
    if (notification.matter_id && onNavigateToMatter) {
      onNavigateToMatter(notification.matter_id);
    }
  };

  return (
    <View style={styles.container}>
      <FlatList
        data={notifications}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <NotificationItem
            notification={item}
            onPress={() => handlePress(item)}
          />
        )}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <EmptyState
            title="No notifications"
            message="You're all caught up. Notifications about deadlines, tasks, and messages will appear here."
          />
        }
        ListHeaderComponent={
          <View style={styles.header}>
            <View>
              <Text style={styles.headerTitle}>Notifications</Text>
              {unreadCount > 0 && (
                <View style={styles.headerActions}>
                  <Badge label={`${unreadCount} new`} color="blue" />
                </View>
              )}
            </View>
            {notifications.length > 0 && (
              <View style={styles.headerButtons}>
                {unreadCount > 0 && (
                  <Button
                    title="Mark all read"
                    variant="ghost"
                    size="sm"
                    onPress={markAllAsRead}
                  />
                )}
                <Button
                  title="Clear"
                  variant="ghost"
                  size="sm"
                  onPress={clearAll}
                />
              </View>
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
    alignItems: "flex-start",
    marginBottom: spacing.lg,
  },
  headerTitle: {
    fontSize: fontSize["2xl"],
    fontWeight: fontWeight.semibold,
    color: colors.foreground,
    letterSpacing: -0.5,
  },
  headerActions: {
    flexDirection: "row",
    gap: spacing.sm,
    marginTop: spacing.xs,
  },
  headerButtons: {
    flexDirection: "row",
    gap: spacing.xs,
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
