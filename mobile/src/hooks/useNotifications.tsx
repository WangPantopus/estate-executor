/**
 * Notification context and hook — manages push registration, notification
 * history, deep link handling, and unread count.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import * as Notifications from "expo-notifications";
import {
  registerForPushNotifications,
  parseNotificationToAppNotification,
  getDeepLinkTarget,
  clearBadge,
  type PushNotificationData,
  type DeepLinkTarget,
} from "@/lib/notifications";
import { cacheGet, cacheSet } from "@/lib/offline-cache";
import type { AppNotification } from "@/lib/types";

const NOTIFICATIONS_CACHE_KEY = "notifications:history";
const MAX_STORED = 50;

interface NotificationContextValue {
  notifications: AppNotification[];
  unreadCount: number;
  pushToken: string | null;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  clearAll: () => void;
  /** Called when a notification tap requires navigation */
  pendingDeepLink: DeepLinkTarget | null;
  consumeDeepLink: () => void;
}

const NotificationContext = createContext<NotificationContextValue | null>(null);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [pushToken, setPushToken] = useState<string | null>(null);
  const [pendingDeepLink, setPendingDeepLink] = useState<DeepLinkTarget | null>(null);
  const notificationListener = useRef<Notifications.EventSubscription>();
  const responseListener = useRef<Notifications.EventSubscription>();

  // Load cached notifications on mount
  useEffect(() => {
    async function loadCached() {
      const cached = await cacheGet<AppNotification[]>(NOTIFICATIONS_CACHE_KEY);
      if (cached) {
        setNotifications(cached);
      }
    }
    loadCached();
  }, []);

  // Persist notifications to cache when they change
  useEffect(() => {
    if (notifications.length > 0) {
      cacheSet(NOTIFICATIONS_CACHE_KEY, notifications.slice(0, MAX_STORED));
    }
  }, [notifications]);

  // Register for push and set up listeners
  useEffect(() => {
    // Register
    registerForPushNotifications().then((token) => {
      if (token) {
        setPushToken(token);
        // In production, send token to backend: api.registerPushToken(token)
      }
    });

    // Foreground notification received
    notificationListener.current = Notifications.addNotificationReceivedListener(
      (notification) => {
        const appNotif = parseNotificationToAppNotification(notification);
        setNotifications((prev) => [appNotif, ...prev].slice(0, MAX_STORED));
      },
    );

    // Notification tapped (background/killed → app opened)
    responseListener.current = Notifications.addNotificationResponseReceivedListener(
      (response) => {
        const data = response.notification.request.content.data as Partial<PushNotificationData>;
        if (data.type && data.matter_id) {
          const target = getDeepLinkTarget(data as PushNotificationData);
          setPendingDeepLink(target);
        }

        // Also add to history if not already there
        const appNotif = parseNotificationToAppNotification(response.notification);
        setNotifications((prev) => {
          if (prev.some((n) => n.id === appNotif.id)) return prev;
          return [{ ...appNotif, read: true }, ...prev].slice(0, MAX_STORED);
        });
      },
    );

    // Check if app was opened from a notification (cold start)
    Notifications.getLastNotificationResponseAsync().then((response) => {
      if (response) {
        const data = response.notification.request.content.data as Partial<PushNotificationData>;
        if (data.type && data.matter_id) {
          setPendingDeepLink(getDeepLinkTarget(data as PushNotificationData));
        }
      }
    });

    return () => {
      notificationListener.current?.remove();
      responseListener.current?.remove();
    };
  }, []);

  const markAsRead = useCallback((id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n)),
    );
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    clearBadge();
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
    cacheSet(NOTIFICATIONS_CACHE_KEY, []);
    clearBadge();
  }, []);

  const consumeDeepLink = useCallback(() => {
    setPendingDeepLink(null);
  }, []);

  const unreadCount = useMemo(
    () => notifications.filter((n) => !n.read).length,
    [notifications],
  );

  const value = useMemo<NotificationContextValue>(
    () => ({
      notifications,
      unreadCount,
      pushToken,
      markAsRead,
      markAllAsRead,
      clearAll,
      pendingDeepLink,
      consumeDeepLink,
    }),
    [notifications, unreadCount, pushToken, markAsRead, markAllAsRead, clearAll, pendingDeepLink, consumeDeepLink],
  );

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications(): NotificationContextValue {
  const ctx = useContext(NotificationContext);
  if (!ctx) {
    throw new Error("useNotifications must be used within a NotificationProvider");
  }
  return ctx;
}
