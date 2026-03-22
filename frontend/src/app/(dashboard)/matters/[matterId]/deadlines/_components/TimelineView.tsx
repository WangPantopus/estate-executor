"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, UserCircle, Link2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/layout/StatusBadge";
import type { DeadlineResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function daysUntil(dateStr: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(dateStr + "T00:00:00");
  return Math.round((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

function formatDate(dateStr: string): string {
  return new Date(dateStr + "T00:00:00").toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function getDaysLabel(days: number): { text: string; className: string } {
  if (days < 0) return { text: `${Math.abs(days)} days overdue`, className: "text-danger font-medium" };
  if (days === 0) return { text: "Due today", className: "text-danger font-medium" };
  if (days === 1) return { text: "Due tomorrow", className: "text-warning font-medium" };
  if (days <= 7) return { text: `${days} days left`, className: "text-warning" };
  if (days <= 30) return { text: `${days} days left`, className: "text-info" };
  return { text: `${days} days left`, className: "text-muted-foreground" };
}

function getTimelineDot(deadline: DeadlineResponse): string {
  if (deadline.status === "completed") return "bg-success";
  if (deadline.status === "missed") return "bg-danger";
  const days = daysUntil(deadline.due_date);
  if (days < 0) return "bg-danger";
  if (days <= 7) return "bg-danger";
  if (days <= 30) return "bg-warning";
  return "bg-info";
}

// ─── Component ────────────────────────────────────────────────────────────────

interface TimelineViewProps {
  deadlines: DeadlineResponse[];
  onDeadlineClick: (deadlineId: string) => void;
}

export function TimelineView({ deadlines, onDeadlineClick }: TimelineViewProps) {
  const [showPast, setShowPast] = useState(false);

  // Sort chronologically
  const sorted = [...deadlines].sort(
    (a, b) => new Date(a.due_date).getTime() - new Date(b.due_date).getTime(),
  );

  const pastDeadlines = sorted.filter(
    (d) => (d.status === "completed" || d.status === "missed") && daysUntil(d.due_date) < 0,
  );
  const activeDeadlines = sorted.filter(
    (d) => !((d.status === "completed" || d.status === "missed") && daysUntil(d.due_date) < 0),
  );

  if (deadlines.length === 0) {
    return (
      <div className="py-12 text-center">
        <p className="text-muted-foreground">No deadlines to show.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Past deadlines (collapsed) */}
      {pastDeadlines.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setShowPast((v) => !v)}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors mb-2"
          >
            {showPast ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
            Past deadlines ({pastDeadlines.length})
          </button>
          {showPast && (
            <div className="space-y-1 mb-4 opacity-60">
              {pastDeadlines.map((d) => (
                <TimelineCard
                  key={d.id}
                  deadline={d}
                  onClick={() => onDeadlineClick(d.id)}
                  muted
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Active / upcoming deadlines */}
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-[15px] top-0 bottom-0 w-px bg-border" />

        <div className="space-y-3">
          {activeDeadlines.map((d) => (
            <TimelineCard
              key={d.id}
              deadline={d}
              onClick={() => onDeadlineClick(d.id)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Timeline Card ────────────────────────────────────────────────────────────

function TimelineCard({
  deadline,
  onClick,
  muted = false,
}: {
  deadline: DeadlineResponse;
  onClick: () => void;
  muted?: boolean;
}) {
  const days = daysUntil(deadline.due_date);
  const daysLabel = getDaysLabel(days);
  const isOverdue = deadline.status === "upcoming" && days < 0;

  return (
    <div
      className={cn(
        "relative flex items-start gap-4 pl-8 cursor-pointer group",
        muted && "opacity-60",
      )}
      onClick={onClick}
    >
      {/* Dot */}
      <div
        className={cn(
          "absolute left-[11px] top-3 size-[10px] rounded-full ring-2 ring-card z-10",
          getTimelineDot(deadline),
        )}
      />

      {/* Card */}
      <div
        className={cn(
          "flex-1 rounded-lg border p-3 transition-all",
          isOverdue
            ? "border-danger/30 bg-danger-light/20 hover:border-danger/50"
            : "border-border bg-card hover:border-primary/30 hover:shadow-sm",
        )}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            {/* Date */}
            <p className="text-xs font-semibold text-foreground">
              {formatDate(deadline.due_date)}
            </p>
            {/* Title */}
            <p className="text-sm font-medium text-foreground mt-0.5 group-hover:text-primary transition-colors">
              {deadline.title}
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <StatusBadge status={deadline.status === "upcoming" && days < 0 ? "missed" : deadline.status} />
          </div>
        </div>

        {/* Meta row */}
        <div className="flex items-center gap-3 mt-2 flex-wrap">
          <span className={cn("text-xs", daysLabel.className)}>
            {daysLabel.text}
          </span>

          {deadline.assignee_name && (
            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
              <UserCircle className="size-3" />
              {deadline.assignee_name}
            </span>
          )}

          {deadline.task && (
            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
              <Link2 className="size-3" />
              {deadline.task.title}
            </span>
          )}

          {deadline.source === "auto" && (
            <Badge variant="muted" className="text-[10px]">Auto</Badge>
          )}
        </div>
      </div>
    </div>
  );
}
