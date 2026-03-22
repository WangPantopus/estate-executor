"use client";

import { AlertTriangle, Clock, CalendarDays, CheckCircle2 } from "lucide-react";
import type { DeadlineResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function daysUntil(dateStr: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(dateStr + "T00:00:00");
  return Math.round((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

// ─── Component ────────────────────────────────────────────────────────────────

interface DeadlineSummaryBarProps {
  deadlines: DeadlineResponse[];
  onFilter: (filter: string) => void;
  activeFilter: string | null;
}

export function DeadlineSummaryBar({
  deadlines,
  onFilter,
  activeFilter,
}: DeadlineSummaryBarProps) {
  const overdue = deadlines.filter(
    (d) => d.status === "upcoming" && daysUntil(d.due_date) < 0,
  ).length;
  const dueThisWeek = deadlines.filter(
    (d) => d.status === "upcoming" && daysUntil(d.due_date) >= 0 && daysUntil(d.due_date) <= 7,
  ).length;
  const dueThisMonth = deadlines.filter(
    (d) => d.status === "upcoming" && daysUntil(d.due_date) > 7 && daysUntil(d.due_date) <= 30,
  ).length;
  const completed = deadlines.filter(
    (d) => d.status === "completed",
  ).length;

  const items = [
    {
      key: "overdue",
      label: "Overdue",
      count: overdue,
      icon: <AlertTriangle className="size-4" />,
      color: "text-danger",
      bg: "bg-danger-light",
      activeBorder: "border-danger",
    },
    {
      key: "this_week",
      label: "Due This Week",
      count: dueThisWeek,
      icon: <Clock className="size-4" />,
      color: "text-warning",
      bg: "bg-warning-light",
      activeBorder: "border-warning",
    },
    {
      key: "this_month",
      label: "Due This Month",
      count: dueThisMonth,
      icon: <CalendarDays className="size-4" />,
      color: "text-info",
      bg: "bg-info-light",
      activeBorder: "border-info",
    },
    {
      key: "completed",
      label: "Completed",
      count: completed,
      icon: <CheckCircle2 className="size-4" />,
      color: "text-success",
      bg: "bg-success-light",
      activeBorder: "border-success",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {items.map((item) => (
        <button
          key={item.key}
          type="button"
          onClick={() =>
            onFilter(activeFilter === item.key ? "" : item.key)
          }
          className={cn(
            "flex items-center gap-3 rounded-lg border-2 p-3 transition-all text-left",
            activeFilter === item.key
              ? `${item.activeBorder} ${item.bg}`
              : "border-border bg-card hover:border-primary/20",
          )}
        >
          <div className={cn("shrink-0", item.color)}>{item.icon}</div>
          <div>
            <p className="text-xl font-semibold text-foreground tabular-nums">
              {item.count}
            </p>
            <p className="text-xs text-muted-foreground">{item.label}</p>
          </div>
        </button>
      ))}
    </div>
  );
}
