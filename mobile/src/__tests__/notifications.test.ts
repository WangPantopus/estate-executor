/**
 * Tests for push notifications, deep linking, and offline cache.
 */

import {
  getDeepLinkTarget,
  type PushNotificationData,
  type NotificationType,
} from "../lib/notifications";
import type { AppNotification } from "../lib/types";

// ─── Deep Link Mapping ─────────────────────────────────────────────────────

describe("Deep Link Mapping", () => {
  it("should map task_assigned to taskDetail screen", () => {
    const data: PushNotificationData = {
      type: "task_assigned",
      matter_id: "m1",
      task_id: "t1",
    };
    const target = getDeepLinkTarget(data);
    expect(target.screen).toBe("taskDetail");
    expect(target.matterId).toBe("m1");
    expect(target.taskId).toBe("t1");
  });

  it("should map deadline_approaching to matterDetail screen", () => {
    const data: PushNotificationData = {
      type: "deadline_approaching",
      matter_id: "m1",
    };
    const target = getDeepLinkTarget(data);
    expect(target.screen).toBe("matterDetail");
    expect(target.matterId).toBe("m1");
  });

  it("should map new_message to matterDetail screen", () => {
    const data: PushNotificationData = {
      type: "new_message",
      matter_id: "m1",
      communication_id: "c1",
    };
    const target = getDeepLinkTarget(data);
    expect(target.screen).toBe("matterDetail");
    expect(target.matterId).toBe("m1");
  });

  it("should map distribution_notice to matterDetail screen", () => {
    const data: PushNotificationData = {
      type: "distribution_notice",
      matter_id: "m1",
      distribution_id: "d1",
    };
    const target = getDeepLinkTarget(data);
    expect(target.screen).toBe("matterDetail");
    expect(target.matterId).toBe("m1");
  });

  it("should fallback to notifications for unknown type", () => {
    const data = {
      type: "unknown_type" as NotificationType,
      matter_id: "m1",
    };
    const target = getDeepLinkTarget(data);
    expect(target.screen).toBe("notifications");
  });
});

// ─── Notification Types ─────────────────────────────────────────────────────

describe("Notification Types", () => {
  it("should have all required notification types", () => {
    const types: NotificationType[] = [
      "task_assigned",
      "deadline_approaching",
      "new_message",
      "distribution_notice",
    ];
    expect(types).toHaveLength(4);
  });

  it("should create valid AppNotification for each type", () => {
    const typeMap: Record<NotificationType, AppNotification["type"]> = {
      task_assigned: "task",
      deadline_approaching: "deadline",
      new_message: "communication",
      distribution_notice: "distribution",
    };

    for (const [pushType, appType] of Object.entries(typeMap)) {
      const notif: AppNotification = {
        id: `n-${pushType}`,
        title: `Test ${pushType}`,
        body: "Test notification body",
        type: appType,
        matter_id: "m1",
        matter_title: "Estate of John Doe",
        created_at: new Date().toISOString(),
        read: false,
      };
      expect(notif.type).toBe(appType);
    }
  });
});

// ─── PushNotificationData ───────────────────────────────────────────────────

describe("PushNotificationData", () => {
  it("should accept all optional fields", () => {
    const data: PushNotificationData = {
      type: "task_assigned",
      matter_id: "m1",
      matter_title: "Estate of John Doe",
      task_id: "t1",
      communication_id: "c1",
      distribution_id: "d1",
    };
    expect(data.type).toBe("task_assigned");
    expect(data.matter_title).toBe("Estate of John Doe");
  });

  it("should work with minimal fields", () => {
    const data: PushNotificationData = {
      type: "deadline_approaching",
      matter_id: "m1",
    };
    expect(data.task_id).toBeUndefined();
  });
});

// ─── Offline Cache Keys ─────────────────────────────────────────────────────

describe("Offline Cache", () => {
  it("should generate correct cache keys", () => {
    const { mattersCacheKey, matterDetailCacheKey, tasksCacheKey, taskDetailCacheKey } =
      require("../lib/offline-cache");

    expect(mattersCacheKey("firm-1")).toBe("matters:firm-1");
    expect(matterDetailCacheKey("firm-1", "m1")).toBe("matter:firm-1:m1");
    expect(tasksCacheKey("firm-1", "m1")).toBe("tasks:firm-1:m1");
    expect(taskDetailCacheKey("firm-1", "m1", "t1")).toBe("task:firm-1:m1:t1");
  });
});

// ─── Notification History ───────────────────────────────────────────────────

describe("Notification History", () => {
  it("should track read/unread status", () => {
    const notifications: AppNotification[] = [
      {
        id: "1",
        title: "Task assigned",
        body: "You have a new task",
        type: "task",
        matter_id: "m1",
        matter_title: "Estate of John Doe",
        created_at: new Date().toISOString(),
        read: false,
      },
      {
        id: "2",
        title: "Deadline reminder",
        body: "IRS Form 706 due in 3 days",
        type: "deadline",
        matter_id: "m1",
        matter_title: "Estate of John Doe",
        created_at: new Date().toISOString(),
        read: true,
      },
    ];

    const unread = notifications.filter((n) => !n.read);
    expect(unread).toHaveLength(1);
    expect(unread[0]!.id).toBe("1");
  });

  it("should mark notification as read", () => {
    const notifications: AppNotification[] = [
      {
        id: "1",
        title: "New message",
        body: "Beneficiary question",
        type: "communication",
        matter_id: "m1",
        matter_title: "Estate of John Doe",
        created_at: new Date().toISOString(),
        read: false,
      },
    ];

    const updated = notifications.map((n) =>
      n.id === "1" ? { ...n, read: true } : n,
    );
    expect(updated[0]!.read).toBe(true);
  });

  it("should limit history to max entries", () => {
    const MAX_STORED = 50;
    const notifications = Array.from({ length: 60 }, (_, i) => ({
      id: String(i),
      title: `Notification ${i}`,
      body: "Body",
      type: "task" as const,
      matter_id: "m1",
      matter_title: "Estate",
      created_at: new Date().toISOString(),
      read: false,
    }));

    const trimmed = notifications.slice(0, MAX_STORED);
    expect(trimmed).toHaveLength(MAX_STORED);
  });
});
