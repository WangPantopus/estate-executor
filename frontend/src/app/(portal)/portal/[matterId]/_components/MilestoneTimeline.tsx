"use client";

import { useMemo } from "react";
import { CheckCircle2, Circle, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Task, EventResponse, Matter } from "@/lib/types";

// Milestone task phases — only show high-level milestones to beneficiaries
const MILESTONE_KEYWORDS = [
  "probate",
  "filed",
  "inventory",
  "appraisal",
  "tax",
  "distribution",
  "notice",
  "closing",
  "letters",
  "certificate",
];

interface Milestone {
  id: string;
  title: string;
  date: string | null;
  status: "completed" | "current" | "upcoming";
  description?: string;
}

function isMilestoneTask(task: Task): boolean {
  const titleLower = task.title.toLowerCase();
  return (
    task.priority === "critical" ||
    MILESTONE_KEYWORDS.some((kw) => titleLower.includes(kw))
  );
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

interface MilestoneTimelineProps {
  tasks: Task[];
  events: EventResponse[];
  matter: Matter;
}

export function MilestoneTimeline({
  tasks,
  events,
  matter,
}: MilestoneTimelineProps) {
  const milestones = useMemo<Milestone[]>(() => {
    // Filter to milestone-worthy tasks
    const milestoneTasks = tasks.filter(isMilestoneTask);

    // Sort: completed first (by completed_at), then in-progress, then not_started
    const sorted = [...milestoneTasks].sort((a, b) => {
      const statusOrder: Record<string, number> = {
        complete: 0,
        waived: 0,
        in_progress: 1,
        blocked: 2,
        not_started: 3,
        cancelled: 4,
      };
      const aOrder = statusOrder[a.status] ?? 3;
      const bOrder = statusOrder[b.status] ?? 3;
      if (aOrder !== bOrder) return aOrder - bOrder;

      // For completed tasks, sort by completion date
      if (a.completed_at && b.completed_at) {
        return (
          new Date(a.completed_at).getTime() -
          new Date(b.completed_at).getTime()
        );
      }
      return a.sort_order - b.sort_order;
    });

    // Find the first non-completed task
    const firstIncompletIdx = sorted.findIndex(
      (t) => t.status !== "complete" && t.status !== "waived",
    );

    return sorted.map((task, i) => {
      const isComplete = task.status === "complete" || task.status === "waived";
      const isCurrent = i === firstIncompletIdx;

      let status: Milestone["status"] = "upcoming";
      if (isComplete) status = "completed";
      else if (isCurrent) status = "current";

      return {
        id: task.id,
        title: task.title,
        date: isComplete ? task.completed_at : task.due_date,
        status,
        description: task.instructions ?? task.description ?? undefined,
      };
    });
  }, [tasks]);

  if (milestones.length === 0) {
    return null;
  }

  return (
    <div className="rounded-xl border border-border bg-card p-6 sm:p-8">
      <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-6">
        Milestones
      </h2>

      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-[15px] top-2 bottom-2 w-px bg-border" />

        <div className="space-y-0">
          {milestones.map((milestone, i) => (
            <div key={milestone.id} className="relative flex gap-4 pb-6 last:pb-0">
              {/* Icon */}
              <div className="relative z-10 shrink-0">
                {milestone.status === "completed" ? (
                  <div className="flex size-[30px] items-center justify-center rounded-full bg-success-light">
                    <CheckCircle2 className="size-4 text-success" />
                  </div>
                ) : milestone.status === "current" ? (
                  <div className="flex size-[30px] items-center justify-center rounded-full bg-gold/15 ring-2 ring-gold/30">
                    <Clock className="size-4 text-gold" />
                  </div>
                ) : (
                  <div className="flex size-[30px] items-center justify-center rounded-full bg-surface-elevated">
                    <Circle className="size-4 text-muted-foreground/40" />
                  </div>
                )}
              </div>

              {/* Content */}
              <div className="pt-0.5 min-w-0">
                <p
                  className={cn(
                    "text-sm leading-snug",
                    milestone.status === "completed"
                      ? "text-foreground"
                      : milestone.status === "current"
                        ? "text-foreground font-medium"
                        : "text-muted-foreground",
                  )}
                >
                  {milestone.title}
                  {milestone.status === "completed" && milestone.date && (
                    <span className="text-muted-foreground">
                      {" "}
                      — {formatDate(milestone.date)}
                    </span>
                  )}
                </p>

                {milestone.status === "current" && (
                  <p className="text-xs text-gold mt-1">
                    {milestone.date
                      ? `Expected by ${formatDate(milestone.date)}`
                      : "In progress"}
                  </p>
                )}

                {milestone.status === "upcoming" && milestone.date && (
                  <p className="text-xs text-muted-foreground/70 mt-0.5">
                    Expected {formatDate(milestone.date)}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
