"use client";

import { useState } from "react";
import {
  X,
  Calendar,
  UserCircle,
  Link2,
  Bell,
  History,
  CheckCircle2,
  Clock,
  Pencil,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { StatusBadge } from "@/components/layout/StatusBadge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useUpdateDeadline, useEvents } from "@/hooks";
import type { DeadlineResponse, Stakeholder, EventResponse } from "@/lib/types";
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
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

const REMINDER_OPTIONS = [
  { days: 30, label: "30 days before" },
  { days: 14, label: "14 days before" },
  { days: 7, label: "7 days before" },
  { days: 3, label: "3 days before" },
  { days: 1, label: "1 day before" },
];

// ─── Panel ────────────────────────────────────────────────────────────────────

interface DeadlineDetailPanelProps {
  deadline: DeadlineResponse;
  firmId: string;
  matterId: string;
  stakeholders: Stakeholder[];
  onClose: () => void;
}

export function DeadlineDetailPanel({
  deadline,
  firmId,
  matterId,
  stakeholders,
  onClose,
}: DeadlineDetailPanelProps) {
  const updateDeadline = useUpdateDeadline(firmId, matterId);
  const { data: eventsData } = useEvents(firmId, matterId, {
    entity_type: "deadline",
    per_page: 20,
  });

  const [editingDate, setEditingDate] = useState(false);
  const [dateValue, setDateValue] = useState(deadline.due_date);

  const days = daysUntil(deadline.due_date);
  const isOverdue = deadline.status === "upcoming" && days < 0;
  const isCompleted = deadline.status === "completed";

  // Parse current reminder config
  const currentReminders: number[] =
    (deadline.reminder_config as { days_before?: number[] } | null)?.days_before ?? [30, 7, 1];

  const deadlineEvents = (eventsData?.data ?? []).filter(
    (e: EventResponse) => e.entity_id === deadline.id,
  );

  const handleComplete = () => {
    updateDeadline.mutate({
      deadlineId: deadline.id,
      data: { status: "completed" },
    });
  };

  const handleExtend = () => {
    // Extend by 30 days
    const current = new Date(deadline.due_date + "T00:00:00");
    current.setDate(current.getDate() + 30);
    const newDate = current.toISOString().split("T")[0];
    updateDeadline.mutate({
      deadlineId: deadline.id,
      data: { due_date: newDate, status: "extended" },
    });
  };

  const handleDateSave = () => {
    updateDeadline.mutate({
      deadlineId: deadline.id,
      data: { due_date: dateValue },
    });
    setEditingDate(false);
  };

  const handleAssign = (stakeholderId: string) => {
    updateDeadline.mutate({
      deadlineId: deadline.id,
      data: { assigned_to: stakeholderId === "__none__" ? null : stakeholderId },
    });
  };

  const toggleReminder = (days: number) => {
    const next = currentReminders.includes(days)
      ? currentReminders.filter((d) => d !== days)
      : [...currentReminders, days].sort((a, b) => b - a);
    updateDeadline.mutate({
      deadlineId: deadline.id,
      data: { reminder_config: { days_before: next } },
    });
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b border-border gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <StatusBadge
              status={isOverdue ? "missed" : deadline.status}
            />
            {deadline.source === "auto" && (
              <Badge variant="muted" className="text-[10px]">Auto-generated</Badge>
            )}
            {deadline.source === "manual" && (
              <Badge variant="outline" className="text-[10px]">Manual</Badge>
            )}
          </div>
          <h2 className="text-lg font-medium text-foreground">{deadline.title}</h2>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} className="shrink-0">
          <X className="size-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-5">
          {/* Description */}
          {deadline.description && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">Description</p>
              <p className="text-sm text-foreground whitespace-pre-wrap">
                {deadline.description}
              </p>
            </div>
          )}

          {/* Due date */}
          <div>
            <h3 className="text-xs font-medium text-muted-foreground mb-2">
              <Calendar className="size-3.5 inline mr-1" />
              Due Date
            </h3>
            {editingDate ? (
              <div className="flex items-center gap-2">
                <Input
                  type="date"
                  value={dateValue}
                  onChange={(e) => setDateValue(e.target.value)}
                  className="flex-1"
                />
                <Button size="sm" onClick={handleDateSave} disabled={updateDeadline.isPending}>
                  Save
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setEditingDate(false)}>
                  Cancel
                </Button>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <p
                  className={cn(
                    "text-sm font-medium",
                    isOverdue ? "text-danger" : "text-foreground",
                  )}
                >
                  {formatDate(deadline.due_date)}
                </p>
                {!isCompleted && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setDateValue(deadline.due_date);
                      setEditingDate(true);
                    }}
                    className="h-7"
                  >
                    <Pencil className="size-3 mr-1" />
                    Edit
                  </Button>
                )}
              </div>
            )}
            {!isCompleted && (
              <p
                className={cn(
                  "text-xs mt-1",
                  isOverdue
                    ? "text-danger font-medium"
                    : days <= 7
                      ? "text-warning"
                      : "text-muted-foreground",
                )}
              >
                {days < 0
                  ? `${Math.abs(days)} days overdue`
                  : days === 0
                    ? "Due today"
                    : `${days} days remaining`}
              </p>
            )}
          </div>

          <Separator />

          {/* Rule explanation (auto-generated) */}
          {deadline.source === "auto" && deadline.rule && (
            <div>
              <h3 className="text-xs font-medium text-muted-foreground mb-2">Rule</h3>
              <div className="rounded-md bg-surface-elevated p-3 text-sm text-foreground">
                {Object.entries(deadline.rule).map(([k, v]) => (
                  <p key={k}>
                    <span className="text-muted-foreground capitalize">{k.replace(/_/g, " ")}:</span>{" "}
                    {String(v)}
                  </p>
                ))}
              </div>
            </div>
          )}

          {/* Assigned to */}
          <div>
            <h3 className="text-xs font-medium text-muted-foreground mb-2">
              <UserCircle className="size-3.5 inline mr-1" />
              Assigned To
            </h3>
            <Select
              value={deadline.assigned_to ?? "__none__"}
              onValueChange={handleAssign}
            >
              <SelectTrigger className="h-9">
                <SelectValue placeholder="Unassigned" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">Unassigned</SelectItem>
                {stakeholders.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    {s.full_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Linked task */}
          {deadline.task && (
            <div>
              <h3 className="text-xs font-medium text-muted-foreground mb-2">
                <Link2 className="size-3.5 inline mr-1" />
                Linked Task
              </h3>
              <div className="rounded-md bg-surface-elevated px-3 py-2 text-sm">
                <p className="font-medium text-foreground">{deadline.task.title}</p>
                <StatusBadge status={deadline.task.status} className="mt-1" />
              </div>
            </div>
          )}

          <Separator />

          {/* Reminder config */}
          <div>
            <h3 className="text-xs font-medium text-muted-foreground mb-2">
              <Bell className="size-3.5 inline mr-1" />
              Reminders
            </h3>
            <div className="space-y-1.5">
              {REMINDER_OPTIONS.map(({ days: d, label }) => (
                <label
                  key={d}
                  className="flex items-center gap-2 text-sm cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={currentReminders.includes(d)}
                    onChange={() => toggleReminder(d)}
                    className="size-3.5 rounded border-border text-primary focus:ring-primary/40"
                  />
                  <span className="text-foreground">{label}</span>
                </label>
              ))}
            </div>
            {deadline.last_reminder_sent && (
              <p className="text-xs text-muted-foreground mt-2">
                Last reminder sent: {formatDateTime(deadline.last_reminder_sent)}
              </p>
            )}
          </div>

          {/* Activity log */}
          {deadlineEvents.length > 0 && (
            <>
              <Separator />
              <div>
                <h3 className="text-xs font-medium text-muted-foreground mb-2">
                  <History className="size-3.5 inline mr-1" />
                  Activity
                </h3>
                <div className="space-y-2">
                  {deadlineEvents.slice(0, 10).map((event: EventResponse) => (
                    <div key={event.id} className="flex items-start gap-2 text-xs">
                      <span className="text-muted-foreground shrink-0">
                        {formatDateTime(event.created_at)}
                      </span>
                      <span className="text-foreground">
                        {event.actor_name ?? event.actor_type} {event.action}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </ScrollArea>

      {/* Action footer */}
      {!isCompleted && (
        <div className="border-t border-border p-4 flex items-center gap-2">
          <Button
            size="sm"
            onClick={handleComplete}
            disabled={updateDeadline.isPending}
            className="flex-1"
          >
            {updateDeadline.isPending ? (
              <Loader2 className="size-4 mr-1 animate-spin" />
            ) : (
              <CheckCircle2 className="size-4 mr-1" />
            )}
            Complete
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleExtend}
            disabled={updateDeadline.isPending}
          >
            <Clock className="size-4 mr-1" />
            Extend 30 days
          </Button>
        </div>
      )}
    </div>
  );
}
