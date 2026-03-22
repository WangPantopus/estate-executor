"use client";

import { useState, useMemo } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { DeadlineResponse, DeadlineStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function daysUntil(dateStr: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(dateStr + "T00:00:00");
  return Math.round((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

function getDeadlineColor(deadline: DeadlineResponse): string {
  if (deadline.status === "completed") return "bg-success";
  if (deadline.status === "missed") return "bg-danger";
  const days = daysUntil(deadline.due_date);
  if (days < 0) return "bg-danger";
  if (days <= 7) return "bg-danger";
  if (days <= 30) return "bg-warning";
  return "bg-info";
}

function getDeadlineDotClass(deadline: DeadlineResponse): string {
  if (deadline.status === "completed") return "bg-success";
  if (deadline.status === "missed") return "bg-danger";
  const days = daysUntil(deadline.due_date);
  if (days < 0) return "bg-danger";
  if (days <= 7) return "bg-danger";
  if (days <= 30) return "bg-warning";
  return "bg-info";
}

function getMonthDays(year: number, month: number) {
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const startPad = firstDay.getDay(); // 0=Sun
  const totalDays = lastDay.getDate();

  const days: { date: Date; inMonth: boolean }[] = [];

  // Pad start
  for (let i = startPad - 1; i >= 0; i--) {
    const d = new Date(year, month, -i);
    days.push({ date: d, inMonth: false });
  }

  // Days in month
  for (let i = 1; i <= totalDays; i++) {
    days.push({ date: new Date(year, month, i), inMonth: true });
  }

  // Pad end to fill 6 rows
  while (days.length < 42) {
    const nextDate = new Date(year, month + 1, days.length - startPad - totalDays + 1);
    days.push({ date: nextDate, inMonth: false });
  }

  return days;
}

function dateKey(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

// ─── Popover ──────────────────────────────────────────────────────────────────

function DayPopover({
  deadlines,
  onDeadlineClick,
  onClose,
}: {
  deadlines: DeadlineResponse[];
  onDeadlineClick: (id: string) => void;
  onClose: () => void;
}) {
  return (
    <div
      className="absolute z-20 top-full left-0 mt-1 w-56 rounded-lg border border-border bg-card shadow-lg p-2 space-y-1"
      onClick={(e) => e.stopPropagation()}
    >
      {deadlines.map((d) => (
        <button
          key={d.id}
          type="button"
          onClick={() => onDeadlineClick(d.id)}
          className="flex items-center gap-2 w-full text-left rounded-md px-2 py-1.5 hover:bg-surface-elevated transition-colors"
        >
          <span className={cn("size-2 rounded-full shrink-0", getDeadlineDotClass(d))} />
          <span className="text-xs text-foreground truncate">{d.title}</span>
        </button>
      ))}
      {deadlines.length === 0 && (
        <p className="text-xs text-muted-foreground text-center py-2">No deadlines</p>
      )}
    </div>
  );
}

// ─── Calendar ─────────────────────────────────────────────────────────────────

interface CalendarViewProps {
  deadlines: DeadlineResponse[];
  onDeadlineClick: (deadlineId: string) => void;
}

export function CalendarView({ deadlines, onDeadlineClick }: CalendarViewProps) {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const [popoverDate, setPopoverDate] = useState<string | null>(null);

  const days = useMemo(() => getMonthDays(year, month), [year, month]);

  // Group deadlines by date
  const deadlinesByDate = useMemo(() => {
    const map = new Map<string, DeadlineResponse[]>();
    for (const d of deadlines) {
      const key = d.due_date;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(d);
    }
    return map;
  }, [deadlines]);

  const goToPrevMonth = () => {
    if (month === 0) {
      setMonth(11);
      setYear(year - 1);
    } else {
      setMonth(month - 1);
    }
  };

  const goToNextMonth = () => {
    if (month === 11) {
      setMonth(0);
      setYear(year + 1);
    } else {
      setMonth(month + 1);
    }
  };

  const goToToday = () => {
    setYear(today.getFullYear());
    setMonth(today.getMonth());
  };

  const todayKey = dateKey(today);

  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={goToPrevMonth} className="size-8">
            <ChevronLeft className="size-4" />
          </Button>
          <h2 className="text-sm font-semibold text-foreground min-w-[160px] text-center">
            {MONTH_NAMES[month]} {year}
          </h2>
          <Button variant="ghost" size="icon" onClick={goToNextMonth} className="size-8">
            <ChevronRight className="size-4" />
          </Button>
        </div>
        <Button variant="outline" size="sm" onClick={goToToday}>
          Today
        </Button>
      </div>

      {/* Weekday headers */}
      <div className="grid grid-cols-7 border-b border-border">
        {WEEKDAYS.map((day) => (
          <div
            key={day}
            className="py-2 text-center text-xs font-medium text-muted-foreground uppercase tracking-wider"
          >
            {day}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7"
        onClick={() => setPopoverDate(null)}
      >
        {days.map(({ date, inMonth }, idx) => {
          const key = dateKey(date);
          const isToday = key === todayKey;
          const dayDeadlines = deadlinesByDate.get(key) ?? [];
          const showPopover = popoverDate === key && dayDeadlines.length > 0;

          return (
            <div
              key={idx}
              className={cn(
                "relative min-h-[80px] sm:min-h-[100px] border-b border-r border-border p-1.5 transition-colors cursor-pointer",
                !inMonth && "bg-surface-elevated/30",
                isToday && "bg-primary/5",
                "hover:bg-surface-elevated/50",
              )}
              onClick={(e) => {
                e.stopPropagation();
                if (dayDeadlines.length > 0) {
                  setPopoverDate(popoverDate === key ? null : key);
                }
              }}
            >
              {/* Date number */}
              <span
                className={cn(
                  "inline-flex items-center justify-center size-6 rounded-full text-xs",
                  isToday
                    ? "bg-primary text-primary-foreground font-semibold"
                    : inMonth
                      ? "text-foreground"
                      : "text-muted-foreground/50",
                )}
              >
                {date.getDate()}
              </span>

              {/* Deadline dots */}
              {dayDeadlines.length > 0 && (
                <div className="mt-1 space-y-0.5">
                  {dayDeadlines.slice(0, 3).map((d) => (
                    <div
                      key={d.id}
                      className={cn(
                        "rounded-sm px-1 py-0.5 text-[10px] font-medium text-white truncate leading-tight",
                        getDeadlineColor(d),
                      )}
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeadlineClick(d.id);
                      }}
                    >
                      {d.title}
                    </div>
                  ))}
                  {dayDeadlines.length > 3 && (
                    <p className="text-[10px] text-muted-foreground px-1">
                      +{dayDeadlines.length - 3} more
                    </p>
                  )}
                </div>
              )}

              {/* Popover */}
              {showPopover && (
                <DayPopover
                  deadlines={dayDeadlines}
                  onDeadlineClick={onDeadlineClick}
                  onClose={() => setPopoverDate(null)}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 px-4 py-2 border-t border-border text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="size-2 rounded-full bg-success" /> Completed
        </span>
        <span className="flex items-center gap-1.5">
          <span className="size-2 rounded-full bg-info" /> Upcoming
        </span>
        <span className="flex items-center gap-1.5">
          <span className="size-2 rounded-full bg-warning" /> Approaching
        </span>
        <span className="flex items-center gap-1.5">
          <span className="size-2 rounded-full bg-danger" /> Urgent / Overdue
        </span>
      </div>
    </div>
  );
}
