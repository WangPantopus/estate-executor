"use client";

import { useEffect, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useSocket, type RealtimeEvent } from "@/components/providers/SocketProvider";
import { useToast } from "@/components/layout/Toaster";
import { queryKeys } from "./use-queries";

const FIRM_ID = "current";

/**
 * Hook for subscribing to real-time WebSocket events for a specific matter.
 *
 * - Joins the matter room on mount, leaves on unmount
 * - Automatically invalidates relevant TanStack Query caches
 * - Shows toast notifications for changes by other users
 *
 * @param matterId - The matter UUID to subscribe to
 */
export function useMatterSocket(matterId: string) {
  const { socket, joinMatter, leaveMatter, status } = useSocket();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Join/leave matter room
  useEffect(() => {
    if (!matterId) return;
    joinMatter(matterId);
    return () => leaveMatter(matterId);
  }, [matterId, joinMatter, leaveMatter]);

  // Handler: invalidate queries based on event type
  const handleEvent = useCallback(
    (eventType: string, data: RealtimeEvent) => {
      switch (eventType) {
        case "task_updated":
          queryClient.invalidateQueries({
            queryKey: ["firms", FIRM_ID, "matters", matterId, "tasks"],
          });
          queryClient.invalidateQueries({
            queryKey: queryKeys.matterDashboard(FIRM_ID, matterId),
          });
          if (data.entity_id) {
            queryClient.invalidateQueries({
              queryKey: queryKeys.task(FIRM_ID, matterId, data.entity_id),
            });
          }
          break;

        case "document_uploaded":
          queryClient.invalidateQueries({
            queryKey: queryKeys.documents(FIRM_ID, matterId),
          });
          if (data.entity_id) {
            queryClient.invalidateQueries({
              queryKey: queryKeys.document(FIRM_ID, matterId, data.entity_id),
            });
          }
          break;

        case "deadline_updated":
          queryClient.invalidateQueries({
            queryKey: ["firms", FIRM_ID, "matters", matterId, "deadlines"],
          });
          queryClient.invalidateQueries({
            queryKey: queryKeys.matterDashboard(FIRM_ID, matterId),
          });
          break;

        case "communication_new":
          queryClient.invalidateQueries({
            queryKey: ["firms", FIRM_ID, "matters", matterId, "communications"],
          });
          break;

        case "stakeholder_changed":
          queryClient.invalidateQueries({
            queryKey: queryKeys.stakeholders(FIRM_ID, matterId),
          });
          queryClient.invalidateQueries({
            queryKey: queryKeys.matterDashboard(FIRM_ID, matterId),
          });
          break;

        case "event_new":
          queryClient.invalidateQueries({
            queryKey: ["firms", FIRM_ID, "matters", matterId, "events"],
          });
          break;
      }
    },
    [queryClient, matterId],
  );

  // Show toast for noteworthy actions by others
  const showToastForEvent = useCallback(
    (eventType: string, data: RealtimeEvent) => {
      // Build a human-readable message
      const action = data.action;
      const entityType = data.entity_type;

      const actionLabels: Record<string, string> = {
        created: "created",
        updated: "updated",
        completed: "completed",
        waived: "waived",
        assigned: "assigned",
        uploaded: "uploaded",
        confirmed: "confirmed",
        removed: "removed",
      };

      const entityLabels: Record<string, string> = {
        task: "a task",
        document: "a document",
        deadline: "a deadline",
        communication: "a message",
        stakeholder: "a stakeholder",
        asset: "an asset",
        entity: "an entity",
      };

      const actionLabel = actionLabels[action] || action;
      const entityLabel = entityLabels[entityType] || entityType;

      // Only toast for specific noteworthy events (not event_new which is generic)
      if (eventType !== "event_new") {
        toast("info", `Someone ${actionLabel} ${entityLabel}`);
      }
    },
    [toast],
  );

  // Subscribe to all Socket.IO events
  useEffect(() => {
    if (!socket) return;

    const events = [
      "task_updated",
      "document_uploaded",
      "deadline_updated",
      "communication_new",
      "stakeholder_changed",
      "event_new",
    ] as const;

    const handlers = events.map((eventType) => {
      const handler = (data: RealtimeEvent) => {
        handleEvent(eventType, data);
        showToastForEvent(eventType, data);
      };
      socket.on(eventType, handler);
      return { eventType, handler };
    });

    return () => {
      for (const { eventType, handler } of handlers) {
        socket.off(eventType, handler);
      }
    };
  }, [socket, handleEvent, showToastForEvent]);

  return { status };
}
