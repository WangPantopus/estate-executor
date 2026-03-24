"use client";

import { CheckCircle2, Circle, Bell, BellOff, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useMilestones, useUpdateMilestoneSetting } from "@/hooks";
import { TASK_PHASE_LABELS } from "@/lib/constants";
import type { MilestoneStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function MilestoneItem({
  milestone,
  isLast,
  firmId,
  matterId,
  isAdmin,
}: {
  milestone: MilestoneStatus;
  isLast: boolean;
  firmId: string;
  matterId: string;
  isAdmin: boolean;
}) {
  const updateSetting = useUpdateMilestoneSetting(firmId, matterId);
  const pct =
    milestone.total_tasks > 0
      ? Math.round((milestone.completed_tasks / milestone.total_tasks) * 100)
      : 0;

  return (
    <div className="flex gap-3">
      {/* Timeline column */}
      <div className="flex flex-col items-center">
        <div
          className={cn(
            "flex items-center justify-center size-7 rounded-full shrink-0 transition-colors",
            milestone.is_complete
              ? "bg-green-100 text-green-600"
              : milestone.completed_tasks > 0
                ? "bg-amber-100 text-amber-600"
                : "bg-gray-100 text-gray-400"
          )}
        >
          {milestone.is_complete ? (
            <CheckCircle2 className="size-4" />
          ) : (
            <Circle className="size-4" />
          )}
        </div>
        {!isLast && (
          <div
            className={cn(
              "w-px flex-1 min-h-[32px]",
              milestone.is_complete ? "bg-green-200" : "bg-border"
            )}
          />
        )}
      </div>

      {/* Content */}
      <div className="pb-5 flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p
              className={cn(
                "text-sm font-medium",
                milestone.is_complete
                  ? "text-green-700"
                  : "text-foreground"
              )}
            >
              {milestone.title}
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {TASK_PHASE_LABELS[milestone.phase] ?? milestone.phase} phase
            </p>
          </div>

          {/* Notification toggle (admin only) */}
          {isAdmin && (
            <Button
              variant="ghost"
              size="icon"
              className="size-7 shrink-0"
              disabled={updateSetting.isPending}
              title={
                milestone.auto_notify
                  ? "Auto-notify enabled — click to disable"
                  : "Auto-notify disabled — click to enable"
              }
              onClick={() =>
                updateSetting.mutate({
                  milestone_key: milestone.key,
                  enabled: !milestone.auto_notify,
                })
              }
            >
              {updateSetting.isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : milestone.auto_notify ? (
                <Bell className="size-3.5 text-primary" />
              ) : (
                <BellOff className="size-3.5 text-muted-foreground" />
              )}
            </Button>
          )}
        </div>

        {/* Progress bar */}
        <div className="mt-2 flex items-center gap-2">
          <div className="h-1.5 flex-1 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-300",
                milestone.is_complete
                  ? "bg-green-500"
                  : pct > 0
                    ? "bg-amber-400"
                    : "bg-gray-200"
              )}
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="text-[10px] text-muted-foreground tabular-nums shrink-0">
            {milestone.completed_tasks}/{milestone.total_tasks}
          </span>
        </div>

        {/* Achieved date */}
        {milestone.achieved_at && (
          <p className="text-[10px] text-green-600 mt-1">
            Achieved {formatDate(milestone.achieved_at)}
          </p>
        )}
      </div>
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

interface MilestoneTimelineProps {
  firmId: string;
  matterId: string;
  isAdmin?: boolean;
}

export function MilestoneTimeline({
  firmId,
  matterId,
  isAdmin = false,
}: MilestoneTimelineProps) {
  const { data, isLoading } = useMilestones(firmId, matterId);
  const milestones = data?.milestones ?? [];

  if (isLoading) {
    return (
      <div className="py-6 text-center">
        <Loader2 className="size-5 animate-spin mx-auto text-muted-foreground" />
      </div>
    );
  }

  if (milestones.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4 text-center">
        No milestones defined.
      </p>
    );
  }

  const completedCount = milestones.filter((m) => m.is_complete).length;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-foreground">Milestones</h3>
        <span className="text-xs text-muted-foreground">
          {completedCount}/{milestones.length} complete
        </span>
      </div>

      {/* Timeline */}
      <div>
        {milestones.map((milestone, i) => (
          <MilestoneItem
            key={milestone.key}
            milestone={milestone}
            isLast={i === milestones.length - 1}
            firmId={firmId}
            matterId={matterId}
            isAdmin={isAdmin}
          />
        ))}
      </div>
    </div>
  );
}
