/**
 * Push notification service — registration, handling, deep linking.
 *
 * Uses Expo Notifications for cross-platform push support.
 * Notification types: task_assigned, deadline_approaching, new_message, distribution_notice
 */

import { Platform } from "react-native";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import Constants from "expo-constants";
import type { AppNotification } from "./types";

// ─── Configuration ──────────────────────────────────────────────────────────

// Set default notification behavior: show alert, play sound, set badge
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
    priority: Notifications.AndroidNotificationPriority.HIGH,
  }),
});

// Android notification channel
if (Platform.OS === "android") {
  Notifications.setNotificationChannelAsync("default", {
    name: "Estate Executor",
    importance: Notifications.AndroidImportance.MAX,
    vibrationPattern: [0, 250, 250, 250],
    lightColor: "#c5a44e",
  });
}

// ─── Notification types ─────────────────────────────────────────────────────

export type NotificationType =
  | "task_assigned"
  | "deadline_approaching"
  | "new_message"
  | "distribution_notice";

export interface PushNotificationData {
  type: NotificationType;
  matter_id: string;
  matter_title?: string;
  task_id?: string;
  communication_id?: string;
  distribution_id?: string;
}

// ─── Deep link mapping ──────────────────────────────────────────────────────

export interface DeepLinkTarget {
  screen: "matterDetail" | "taskDetail" | "notifications";
  matterId?: string;
  taskId?: string;
}

export function getDeepLinkTarget(data: PushNotificationData): DeepLinkTarget {
  switch (data.type) {
    case "task_assigned":
      return {
        screen: "taskDetail",
        matterId: data.matter_id,
        taskId: data.task_id,
      };
    case "deadline_approaching":
      return {
        screen: "matterDetail",
        matterId: data.matter_id,
      };
    case "new_message":
      return {
        screen: "matterDetail",
        matterId: data.matter_id,
      };
    case "distribution_notice":
      return {
        screen: "matterDetail",
        matterId: data.matter_id,
      };
    default:
      return { screen: "notifications" };
  }
}

// ─── Token registration ─────────────────────────────────────────────────────

export async function registerForPushNotifications(): Promise<string | null> {
  // Push only works on physical devices
  if (!Device.isDevice) {
    console.log("Push notifications require a physical device");
    return null;
  }

  // Check existing permissions
  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  // Request if not granted
  if (existingStatus !== "granted") {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== "granted") {
    console.log("Push notification permission not granted");
    return null;
  }

  // Get Expo push token
  try {
    const projectId = Constants.expoConfig?.extra?.eas?.projectId;
    const tokenData = await Notifications.getExpoPushTokenAsync({
      projectId: projectId ?? undefined,
    });
    return tokenData.data;
  } catch (error) {
    console.error("Failed to get push token:", error);
    return null;
  }
}

// ─── Parse notification into AppNotification ────────────────────────────────

export function parseNotificationToAppNotification(
  notification: Notifications.Notification,
): AppNotification {
  const data = (notification.request.content.data ?? {}) as Partial<PushNotificationData>;
  const content = notification.request.content;

  const typeMap: Record<string, AppNotification["type"]> = {
    task_assigned: "task",
    deadline_approaching: "deadline",
    new_message: "communication",
    distribution_notice: "distribution",
  };

  return {
    id: notification.request.identifier,
    title: content.title ?? "Notification",
    body: content.body ?? "",
    type: typeMap[data.type ?? ""] ?? "task",
    matter_id: data.matter_id ?? "",
    matter_title: data.matter_title ?? "",
    created_at: new Date(notification.date * 1000).toISOString(),
    read: false,
  };
}

// ─── Schedule local notification (for testing) ──────────────────────────────

export async function scheduleLocalNotification(
  title: string,
  body: string,
  data: PushNotificationData,
  delaySeconds: number = 1,
): Promise<string> {
  return Notifications.scheduleNotificationAsync({
    content: {
      title,
      body,
      data: data as unknown as Record<string, unknown>,
      sound: true,
    },
    trigger: {
      type: Notifications.SchedulableTriggerInputTypes.TIME_INTERVAL,
      seconds: delaySeconds,
    },
  });
}

// ─── Get delivered notifications ────────────────────────────────────────────

export async function getDeliveredNotifications(): Promise<AppNotification[]> {
  const delivered = await Notifications.getPresentedNotificationsAsync();
  return delivered.map((n) => parseNotificationToAppNotification(n));
}

// ─── Clear badge ────────────────────────────────────────────────────────────

export async function clearBadge(): Promise<void> {
  await Notifications.setBadgeCountAsync(0);
}

// ─── Dismiss all notifications ──────────────────────────────────────────────

export async function dismissAllNotifications(): Promise<void> {
  await Notifications.dismissAllNotificationsAsync();
  await clearBadge();
}
