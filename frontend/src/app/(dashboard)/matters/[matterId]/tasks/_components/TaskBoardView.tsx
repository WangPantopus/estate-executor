"use client";

import { useState, useCallback } from "react";
import { UserCircle, GripVertical } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { TASK_STATUS_LABELS } from "@/lib/constants";
import type { Task, Stakeholder, TaskStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

const BOARD_COLUMNS: TaskStatus[] = ["not_started", "in_progress", "blocked", "complete"];

interface TaskBoardViewProps {
  tasks: Task[];
  stakeholders: Stakeholder[];
  onTaskClick: (taskId: string) => void;
  onStatusChange: (taskId: string, newStatus: TaskStatus) => void;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function isOverdue(task: Task): boolean {
  if (!task.due_date) return false;
  if (task.status === "complete" || task.status === "waived" || task.status === "cancelled") return false;
  return new Date(task.due_date) < new Date(new Date().toDateString());
}

function formatDueDate(dateStr: string): string {
  const date = new Date(dateStr + "T00:00:00");
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function getStakeholderName(id: string | null, stakeholders: Stakeholder[]): string {
  if (!id) return "";
  return stakeholders.find((s) => s.id === id)?.full_name ?? "";
}

// ─── Card ─────────────────────────────────────────────────────────────────────

function TaskCard({
  task,
  stakeholders,
  onClick,
  onDragStart,
}: {
  task: Task;
  stakeholders: Stakeholder[];
  onClick: () => void;
  onDragStart: (e: React.DragEvent) => void;
}) {
  const overdue = isOverdue(task);
  const assigneeName = getStakeholderName(task.assigned_to, stakeholders);

  return (
    <div
      draggable
      onDragStart={onDragStart}
      onClick={onClick}
      className={cn(
        "group rounded-lg border border-border bg-card p-3 shadow-sm cursor-pointer transition-all",
        "hover:shadow-md hover:border-primary/30",
        "active:cursor-grabbing",
        overdue && "border-l-2 border-l-danger",
      )}
    >
      <div className="flex items-start gap-2">
        <GripVertical className="size-3.5 text-muted-foreground opacity-0 group-hover:opacity-50 shrink-0 mt-0.5 cursor-grab" />
        <div className="flex-1 min-w-0">
          {/* Title + priority */}
          <div className="flex items-center gap-1.5">
            {task.priority === "critical" && (
              <span className="size-2 rounded-full bg-danger shrink-0" />
            )}
            {task.priority === "informational" && (
              <span className="size-2 rounded-full bg-info shrink-0" />
            )}
            <p className="text-sm font-medium text-foreground truncate">{task.title}</p>
          </div>

          {/* Meta row */}
          <div className="flex items-center gap-3 mt-2">
            {assigneeName && (
              <span className="inline-flex items-center gap-1 text-xs text-muted-foreground truncate max-w-[100px]">
                <UserCircle className="size-3" />
                {assigneeName}
              </span>
            )}
            {task.due_date && (
              <span
                className={cn(
                  "text-xs",
                  overdue ? "text-danger font-medium" : "text-muted-foreground",
                )}
              >
                {formatDueDate(task.due_date)}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Column ───────────────────────────────────────────────────────────────────

function BoardColumn({
  status,
  tasks,
  stakeholders,
  onTaskClick,
  onDrop,
  dragOverStatus,
  onDragOver,
  onDragLeave,
}: {
  status: TaskStatus;
  tasks: Task[];
  stakeholders: Stakeholder[];
  onTaskClick: (taskId: string) => void;
  onDrop: (e: React.DragEvent) => void;
  dragOverStatus: TaskStatus | null;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: () => void;
}) {
  const isOver = dragOverStatus === status;

  return (
    <div
      className={cn(
        "flex flex-col rounded-lg bg-surface-elevated/50 border border-border min-w-[260px] w-[280px] shrink-0 transition-colors",
        isOver && "border-primary/50 bg-primary/5",
      )}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-border">
        <span className="text-sm font-medium text-foreground">
          {TASK_STATUS_LABELS[status] ?? status}
        </span>
        <span className="text-xs text-muted-foreground bg-surface rounded-full px-2 py-0.5">
          {tasks.length}
        </span>
      </div>

      {/* Cards */}
      <ScrollArea className="flex-1 max-h-[calc(100vh-320px)]">
        <div className="p-2 space-y-2 min-h-[60px]">
          {tasks.length === 0 && (
            <p className="text-xs text-muted-foreground text-center py-4">No tasks</p>
          )}
          {tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              stakeholders={stakeholders}
              onClick={() => onTaskClick(task.id)}
              onDragStart={(e) => {
                e.dataTransfer.setData("text/plain", task.id);
                e.dataTransfer.effectAllowed = "move";
              }}
            />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}

// ─── Board View ───────────────────────────────────────────────────────────────

export function TaskBoardView({
  tasks,
  stakeholders,
  onTaskClick,
  onStatusChange,
}: TaskBoardViewProps) {
  const [dragOverStatus, setDragOverStatus] = useState<TaskStatus | null>(null);

  const tasksByStatus = BOARD_COLUMNS.reduce(
    (acc, status) => {
      acc[status] = tasks.filter((t) => t.status === status);
      return acc;
    },
    {} as Record<TaskStatus, Task[]>,
  );

  // Also show waived tasks in complete column
  tasksByStatus.complete = [
    ...tasksByStatus.complete,
    ...tasks.filter((t) => t.status === "waived" || t.status === "cancelled"),
  ];

  const handleDragOver = useCallback(
    (status: TaskStatus) => (e: React.DragEvent) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      setDragOverStatus(status);
    },
    [],
  );

  const handleDrop = useCallback(
    (targetStatus: TaskStatus) => (e: React.DragEvent) => {
      e.preventDefault();
      setDragOverStatus(null);
      const taskId = e.dataTransfer.getData("text/plain");
      if (taskId) {
        onStatusChange(taskId, targetStatus);
      }
    },
    [onStatusChange],
  );

  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {BOARD_COLUMNS.map((status) => (
        <BoardColumn
          key={status}
          status={status}
          tasks={tasksByStatus[status]}
          stakeholders={stakeholders}
          onTaskClick={onTaskClick}
          onDrop={handleDrop(status)}
          dragOverStatus={dragOverStatus}
          onDragOver={handleDragOver(status)}
          onDragLeave={() => setDragOverStatus(null)}
        />
      ))}
    </div>
  );
}
