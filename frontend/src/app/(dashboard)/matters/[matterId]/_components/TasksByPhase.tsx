"use client";

import { useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronRight, AlertCircle } from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/layout/StatusBadge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { useCompleteTask } from "@/hooks";
import type { Task, TaskPhase, TaskStatus } from "@/lib/types";

const PHASE_ORDER: { key: TaskPhase; label: string }[] = [
  { key: "immediate", label: "Immediate" },
  { key: "asset_inventory", label: "Asset Inventory" },
  { key: "notification", label: "Notification" },
  { key: "probate_filing", label: "Probate Filing" },
  { key: "tax", label: "Tax" },
  { key: "transfer_distribution", label: "Transfer & Distribution" },
  { key: "family_communication", label: "Family Communication" },
  { key: "closing", label: "Closing" },
  { key: "custom", label: "Custom" },
];

interface TasksByPhaseProps {
  tasks: Task[];
  firmId: string;
  matterId: string;
}

export function TasksByPhase({ tasks, firmId, matterId }: TasksByPhaseProps) {
  // Group tasks by phase
  const grouped = PHASE_ORDER.map((phase) => ({
    ...phase,
    tasks: tasks.filter((t) => t.phase === phase.key),
  })).filter((g) => g.tasks.length > 0);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Tasks by Phase</CardTitle>
        <Button variant="ghost" size="sm" asChild>
          <Link href={`/matters/${matterId}/tasks`}>View all</Link>
        </Button>
      </CardHeader>
      <CardContent className="space-y-1 pt-0">
        {grouped.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4 text-center">
            No tasks yet. Generate tasks from the matter settings.
          </p>
        ) : (
          grouped.map((group) => (
            <PhaseSection
              key={group.key}
              label={group.label}
              tasks={group.tasks}
              firmId={firmId}
              matterId={matterId}
            />
          ))
        )}
      </CardContent>
    </Card>
  );
}

function PhaseSection({
  label,
  tasks,
  firmId,
  matterId,
}: {
  label: string;
  tasks: Task[];
  firmId: string;
  matterId: string;
}) {
  const [open, setOpen] = useState(true);
  const completedCount = tasks.filter(
    (t) => t.status === "complete" || t.status === "waived",
  ).length;

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md px-3 py-2.5 text-sm hover:bg-surface-elevated transition-colors">
        {open ? (
          <ChevronDown className="size-4 text-muted-foreground shrink-0" />
        ) : (
          <ChevronRight className="size-4 text-muted-foreground shrink-0" />
        )}
        <span className="font-medium flex-1 text-left">{label}</span>
        <span className="text-xs text-muted-foreground">
          {completedCount}/{tasks.length}
        </span>
        {/* Mini progress */}
        <div className="w-16 h-1.5 rounded-full bg-surface-elevated overflow-hidden">
          <div
            className="h-full rounded-full bg-primary transition-all duration-300"
            style={{
              width: `${tasks.length ? (completedCount / tasks.length) * 100 : 0}%`,
            }}
          />
        </div>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="ml-6 border-l border-border pl-3 space-y-0.5 py-1">
          {tasks.slice(0, 10).map((task) => (
            <TaskRow
              key={task.id}
              task={task}
              firmId={firmId}
              matterId={matterId}
            />
          ))}
          {tasks.length > 10 && (
            <p className="text-xs text-muted-foreground py-1 pl-7">
              +{tasks.length - 10} more tasks
            </p>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

function TaskRow({
  task,
  firmId,
  matterId,
}: {
  task: Task;
  firmId: string;
  matterId: string;
}) {
  const completeTask = useCompleteTask(firmId, matterId);
  const isDone = task.status === "complete" || task.status === "waived";
  const isOverdue =
    task.due_date && new Date(task.due_date) < new Date() && !isDone;
  const isCritical = task.priority === "critical";

  const handleComplete = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDone) {
      completeTask.mutate({ taskId: task.id });
    }
  };

  return (
    <div
      className={`flex items-center gap-2 rounded-md px-2 py-2 text-sm transition-colors hover:bg-surface-elevated ${
        isOverdue ? "border-l-2 border-l-danger -ml-px" : ""
      }`}
    >
      {/* Checkbox */}
      <button
        onClick={handleComplete}
        disabled={isDone}
        className={`flex size-4 shrink-0 items-center justify-center rounded border transition-colors ${
          isDone
            ? "bg-primary border-primary text-primary-foreground"
            : "border-border hover:border-primary"
        }`}
      >
        {isDone && (
          <svg
            width="10"
            height="10"
            viewBox="0 0 10 10"
            fill="none"
            className="text-primary-foreground"
          >
            <path
              d="M2 5L4 7L8 3"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
      </button>

      {/* Critical indicator */}
      {isCritical && (
        <AlertCircle className="size-3.5 text-danger shrink-0" />
      )}

      {/* Title */}
      <span
        className={`flex-1 truncate ${
          isDone ? "line-through text-muted-foreground" : "text-foreground"
        }`}
      >
        {task.title}
      </span>

      {/* Due date */}
      {task.due_date && (
        <span
          className={`text-xs shrink-0 ${
            isOverdue ? "text-danger font-medium" : "text-muted-foreground"
          }`}
        >
          {new Date(task.due_date).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
          })}
        </span>
      )}

      {/* Status */}
      {!isDone && task.status !== "not_started" && (
        <StatusBadge status={task.status as TaskStatus} />
      )}
    </div>
  );
}
